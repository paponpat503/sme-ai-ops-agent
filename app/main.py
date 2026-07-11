from __future__ import annotations
from pathlib import Path
from contextlib import asynccontextmanager
import uuid
import hmac
import ipaddress
import re

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.schemas.models import (
    AskAgentResponse,
    AskRequest,
    RagSearchRequest,
    RagSearchResponse,
    ToolCallRequest,
    ToolCallResponse,
)
from app.agents.llm_ops_agent import answer_with_agent_result
from app.rag.runtime import rag_runtime
from app.tools.registry import call_registered_tool, list_registered_tools
from app.config import get_settings, validate_production_settings
from app.security.context import PrincipalContext, reset_principal, set_principal
from app.data.repositories import get_business_repository, set_business_repository
from app.rate_limit import SlidingWindowRateLimiter
from app.tools.transport import tool_transport_is_ready

@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    settings = get_settings()
    if settings.database_url:
        from app.data.sql_repository import SqlAlchemyBusinessRepository
        set_business_repository(SqlAlchemyBusinessRepository(settings.database_url))
    try:
        rag_runtime.build()
    except Exception:
        # Keep liveness available while readiness reports the dependency failure.
        pass
    yield


app = FastAPI(
    title="SME AI Ops Agent",
    description="B2B AI automation demo: RAG, structured outputs, tool-calling architecture, and CRM workflow intelligence.",
    version="0.2.0",
    lifespan=lifespan,
)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
_rate_limiter: SlidingWindowRateLimiter | None = None


def _get_rate_limiter() -> SlidingWindowRateLimiter:
    global _rate_limiter
    settings = get_settings()
    if _rate_limiter is None or (
        _rate_limiter.limit != settings.rate_limit_requests
        or _rate_limiter.window_seconds != settings.rate_limit_window_seconds
        or _rate_limiter.max_clients != settings.rate_limit_max_clients
    ):
        _rate_limiter = SlidingWindowRateLimiter(
            settings.rate_limit_requests,
            settings.rate_limit_window_seconds,
            settings.rate_limit_max_clients,
        )
    return _rate_limiter


def _client_key(request: Request, trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def _request_id(request: Request) -> str:
    supplied = request.headers.get("x-request-id", "")
    if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", supplied):
        return supplied
    return str(uuid.uuid4())


@app.middleware("http")
async def production_boundary(request: Request, call_next):
    settings = get_settings()
    request_id = _request_id(request)
    public_path = request.url.path in {"/", "/demo", "/live", "/health", "/ready", "/docs", "/openapi.json"} or request.url.path.startswith("/static/")

    try:
        content_length = int(request.headers.get("content-length", "0") or 0)
    except ValueError:
        return JSONResponse({"detail": "Invalid Content-Length header."}, status_code=400)
    if content_length < 0:
        return JSONResponse({"detail": "Invalid Content-Length header."}, status_code=400)
    if content_length > settings.max_request_body_bytes:
        return JSONResponse({"detail": "Request body too large."}, status_code=413)
    if request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        if len(body) > settings.max_request_body_bytes:
            return JSONResponse({"detail": "Request body too large."}, status_code=413)

    rate_headers: dict[str, str] = {}
    if request.url.path.startswith(("/agent/", "/rag/", "/tools/")):
        decision = _get_rate_limiter().check(_client_key(request, settings.trust_proxy_headers))
        rate_headers = {
            "X-RateLimit-Limit": str(settings.rate_limit_requests),
            "X-RateLimit-Remaining": str(decision.remaining),
        }
        if not decision.allowed:
            rate_headers["Retry-After"] = str(decision.retry_after_seconds)
            return JSONResponse({"detail": "Rate limit exceeded."}, status_code=429, headers=rate_headers)

    if settings.app_env == "production" and not public_path:
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        identity = settings.api_keys.get(supplied)
        legacy_key_valid = bool(settings.api_key and hmac.compare_digest(supplied, settings.api_key))
        if not identity and not legacy_key_valid:
            return JSONResponse({"detail": "Authentication required."}, status_code=401)
    else:
        identity = None

    principal = PrincipalContext(
        tenant_id=identity.tenant_id if identity else settings.demo_tenant_id,
        user_id=identity.user_id if identity else ("demo-user" if settings.app_env != "production" else "api-user"),
        roles=frozenset(identity.roles) if identity else frozenset({"operator"}),
        request_id=request_id,
    )
    token = set_principal(principal)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        for name, value in rate_headers.items():
            response.headers[name] = value
        return response
    finally:
        reset_principal(token)

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "sme-ai-ops-agent"}


@app.get("/live")
def liveness() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def readiness() -> JSONResponse:
    settings = get_settings()
    checks = {
        "retrieval": rag_runtime.is_ready(),
        "data": get_business_repository().is_ready(),
        "tool_transport": tool_transport_is_ready(settings.tool_transport),
    }
    failed = [name for name, ready in checks.items() if not ready]
    if failed:
        return JSONResponse(
            {"status": "not_ready", "checks": checks, "failed_dependencies": failed},
            status_code=503,
        )
    return JSONResponse({"status": "ready", "checks": checks})

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/demo")

@app.get("/demo", include_in_schema=False)
def demo_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "demo.html")

@app.post("/agent/ask", response_model=AskAgentResponse)
def ask_agent(payload: AskRequest) -> AskAgentResponse:
    result = answer_with_agent_result(payload.question)
    return AskAgentResponse(
        answer=result.answer,
        metadata=result.metadata,
        tool_trace=result.tool_trace,
    )

@app.post("/rag/search", response_model=RagSearchResponse)
def search_rag(payload: RagSearchRequest) -> RagSearchResponse:
    hits = rag_runtime.search(payload.query, payload.top_k)
    return RagSearchResponse(query=payload.query, hits=hits)

@app.post("/tools/call", response_model=ToolCallResponse)
def call_tool(payload: ToolCallRequest) -> ToolCallResponse | JSONResponse:
    response = call_registered_tool(payload.tool_name, payload.arguments)
    payload_out = ToolCallResponse(
        tool_name=response.tool_name,
        result=response.result,
        error=response.error,
        error_code=response.error_code,
    )
    if response.error_code:
        status_by_code = {
            "unknown_tool": 404,
            "forbidden": 403,
            "invalid_arguments": 422,
            "execution_error": 502,
        }
        return JSONResponse(payload_out.model_dump(), status_code=status_by_code[response.error_code])
    return payload_out

@app.get("/tools/list")
def list_tools() -> dict:
    return {"tools": list_registered_tools()}
