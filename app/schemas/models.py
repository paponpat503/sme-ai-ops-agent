from __future__ import annotations
from typing import Any, Literal, Optional, List
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

RiskLevel = Literal["low", "medium", "high", "critical"]
ToolErrorCode = Literal["unknown_tool", "forbidden", "invalid_arguments", "execution_error"]
ActionType = Literal[
    "send_followup_email",
    "schedule_support_call",
    "create_crm_task",
    "escalate_to_manager",
    "no_action",
]

class AskRequest(StrictModel):
    question: str = Field(..., min_length=3, max_length=2000)

AgentMode = Literal["deterministic", "llm", "auto", "tool_agent"]
ValidationStatus = Literal[
    "not_attempted",
    "valid",
    "provider_unavailable",
    "invalid_fallback",
]

class CustomerAction(StrictModel):
    customer_id: str
    customer_name: str
    risk_level: RiskLevel
    reason: str
    recommended_action: ActionType
    priority_score: int = Field(..., ge=0, le=100)
    draft_message: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)

class AgentAnswer(StrictModel):
    intent: str
    summary: str
    actions: List[CustomerAction] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]

class AgentRunMetadata(StrictModel):
    agent_mode: AgentMode
    provider_used: str
    fallback_used: bool
    validation_status: ValidationStatus
    error: Optional[str] = None
    tool_agent_used: bool = False
    tool_calls_count: int = 0
    tools_called: List[str] = Field(default_factory=list)
    request_id: str = "local"
    tenant_id: str = "demo"
    latency_ms: float = Field(default=0.0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    fallback_reason: Optional[str] = None

class ToolCallPlan(StrictModel):
    tool_name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str
    depends_on: List[int] = Field(default_factory=list)

class ToolCallResult(StrictModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    error_code: Optional[ToolErrorCode] = None
    latency_ms: float = Field(default=0.0, ge=0)
    validation_status: Literal["valid", "rejected", "execution_error"] = "valid"

class ToolAgentTrace(StrictModel):
    plan: List[ToolCallPlan] = Field(default_factory=list)
    results: List[ToolCallResult] = Field(default_factory=list)
    planner: Literal["deterministic", "llm"] = "deterministic"
    transport: Literal["local", "mcp"] = "local"


class ToolPlan(StrictModel):
    calls: List[ToolCallPlan] = Field(default_factory=list, max_length=5)

class AskAgentResponse(StrictModel):
    answer: AgentAnswer
    metadata: AgentRunMetadata
    tool_trace: Optional[ToolAgentTrace] = None

class ToolCallRequest(StrictModel):
    tool_name: str = Field(..., min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)

class ToolCallResponse(StrictModel):
    tool_name: str
    result: Any = None
    error: Optional[str] = None
    error_code: Optional[ToolErrorCode] = None

class RagSearchRequest(StrictModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)

class RagHit(StrictModel):
    doc_id: str
    source: str
    score: float
    text: str
    tenant_id: str = "demo"
    section: str = ""
    version: str = "1"

class RagSearchResponse(StrictModel):
    query: str
    hits: List[RagHit]

class EvalCase(StrictModel):
    id: str
    question: str
    expected_intent: str
    must_include_customers: List[str] = Field(default_factory=list)
    must_not_include_customers: List[str] = Field(default_factory=list)
    required_action_types: List[ActionType] = Field(default_factory=list)
