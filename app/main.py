from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
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
from app.rag.simple_rag import rag_index
from app.tools.registry import call_registered_tool, list_registered_tools

app = FastAPI(title="SME AI Ops Agent", description="B2B AI automation demo: RAG, structured outputs, tool-calling architecture, and CRM workflow intelligence.", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def startup() -> None:
    rag_index.build()

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "sme-ai-ops-agent"}

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
    hits = rag_index.search(payload.query, payload.top_k)
    return RagSearchResponse(query=payload.query, hits=hits)

@app.post("/tools/call", response_model=ToolCallResponse)
def call_tool(payload: ToolCallRequest) -> ToolCallResponse:
    response = call_registered_tool(payload.tool_name, payload.arguments)
    return ToolCallResponse(
        tool_name=response.tool_name,
        result=response.result,
        error=response.error,
    )

@app.get("/tools/list")
def list_tools() -> dict:
    return {"tools": list_registered_tools()}
