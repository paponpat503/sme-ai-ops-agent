from __future__ import annotations
from typing import Any, Literal, Optional, List
from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high", "critical"]
ActionType = Literal[
    "send_followup_email",
    "schedule_support_call",
    "create_crm_task",
    "escalate_to_manager",
    "no_action",
]

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)

AgentMode = Literal["deterministic", "llm", "auto", "tool_agent"]
ValidationStatus = Literal[
    "not_attempted",
    "valid",
    "provider_unavailable",
    "invalid_fallback",
]

class CustomerAction(BaseModel):
    customer_id: str
    customer_name: str
    risk_level: RiskLevel
    reason: str
    recommended_action: ActionType
    priority_score: int = Field(..., ge=0, le=100)
    draft_message: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)

class AgentAnswer(BaseModel):
    intent: str
    summary: str
    actions: List[CustomerAction] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]

class AgentRunMetadata(BaseModel):
    agent_mode: AgentMode
    provider_used: str
    fallback_used: bool
    validation_status: ValidationStatus
    error: Optional[str] = None
    tool_agent_used: bool = False
    tool_calls_count: int = 0
    tools_called: List[str] = Field(default_factory=list)

class ToolCallPlan(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str

class ToolCallResult(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None

class ToolAgentTrace(BaseModel):
    plan: List[ToolCallPlan] = Field(default_factory=list)
    results: List[ToolCallResult] = Field(default_factory=list)

class AskAgentResponse(BaseModel):
    answer: AgentAnswer
    metadata: AgentRunMetadata
    tool_trace: Optional[ToolAgentTrace] = None

class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)

class ToolCallResponse(BaseModel):
    tool_name: str
    result: Any = None
    error: Optional[str] = None

class RagSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=10)

class RagHit(BaseModel):
    doc_id: str
    source: str
    score: float
    text: str

class RagSearchResponse(BaseModel):
    query: str
    hits: List[RagHit]

class EvalCase(BaseModel):
    id: str
    question: str
    expected_intent: str
    must_include_customers: List[str] = Field(default_factory=list)
    must_not_include_customers: List[str] = Field(default_factory=list)
    required_action_types: List[ActionType] = Field(default_factory=list)
