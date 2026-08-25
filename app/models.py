from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Role = Literal["anonymous", "customer", "customer_service", "auditor", "administrator"]
RiskLevel = Literal["low", "medium", "high", "critical"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ToolContract(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_roles: list[Role]
    high_risk: bool
    requires_approval: bool
    idempotency_key: str | None
    timeout_ms: int
    errors: list[str]
    data_scope: str
    redaction_rules: list[str]


class PolicyDecision(BaseModel):
    policy_id: str
    decision: Literal["allow", "deny", "require_approval"]
    reason: str
    risk_level: RiskLevel
    related_tool: str | None = None
    related_trace_id: str
    timestamp: datetime = Field(default_factory=utc_now)


class FaultCreate(BaseModel):
    target_tool: str
    fault_type: Literal[
        "timeout", "http_500", "http_429", "empty_response", "missing_field",
        "wrong_field_type", "malformed_json", "duplicate_callback", "stale_data",
        "database_unavailable", "partial_success", "idempotency_conflict",
        "malicious_tool_output", "indirect_prompt_injection", "permission_service_unavailable"
    ]
    trigger_count: int = Field(default=1, ge=1, le=20)
    enabled: bool = True


class FaultRecord(FaultCreate):
    fault_id: str
    remaining_count: int
    created_at: datetime = Field(default_factory=utc_now)


class AgentRunRequest(BaseModel):
    user_input: str = Field(min_length=2, max_length=1200)
    user_role: Role = "anonymous"
    actor_id: str | None = Field(default=None, max_length=40)
    target_object: str | None = Field(default=None, max_length=80)
    available_tools: list[str] | None = None
    confirm_second_factor: bool = False
    human_approval_id: str | None = Field(default=None, max_length=80)
    idempotency_key: str | None = Field(default=None, max_length=100)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("actor_id", "target_object", "human_approval_id", "idempotency_key")
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        if value and any(ord(char) < 32 for char in value):
            raise ValueError("control characters are not allowed")
        return value


class ToolEvent(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    status: Literal["success", "blocked", "failed", "pending_approval", "replayed"]
    response: dict[str, Any] | None = None
    error: str | None = None
    attempt: int = 1
    duration_ms: float = 0
    side_effect: bool = False
    fault_type: str | None = None


class RetrievedChunk(BaseModel):
    source: str
    text: str
    score: float = Field(ge=0)
    malicious: bool = False


class TraceRecord(BaseModel):
    trace_id: str
    request_id: str
    created_at: datetime = Field(default_factory=utc_now)
    user_input: str
    user_role: Role
    actor_id: str | None
    target_object: str | None
    retrieved_context: list[RetrievedChunk]
    provider: str
    model: str
    prompt_version: str
    policy_version: str
    decision: str
    tool_events: list[ToolEvent]
    policy_decisions: list[PolicyDecision]
    approval_status: str
    final_answer: str
    step_durations_ms: dict[str, float]
    total_duration_ms: float
    estimated_tokens: int
    estimated_cost_usd: float
    success: bool
    failure_reason: str | None
    risk_tags: list[str]
    replay_of: str | None = None


class AgentRunResponse(BaseModel):
    request_id: str
    trace_id: str
    success: bool
    answer: str
    status: str
    tool_events: list[ToolEvent]
    policy_decisions: list[PolicyDecision]
    risk_tags: list[str]
    citations: list[str]
    total_duration_ms: float


class ReplayRequest(BaseModel):
    mode: Literal["original", "new_prompt", "new_policy", "new_provider"] = "original"
    prompt_version: str | None = None
    policy_version: str | None = None
    provider: str | None = None
    offline: bool = True


class ReplayComparison(BaseModel):
    baseline_trace_id: str
    candidate_trace_id: str
    tool_selection_changes: list[str]
    argument_changes: list[str]
    policy_changes: list[str]
    new_failures: list[str]
    recovered_cases: list[str]
    latency_delta_ms: float
    cost_delta_usd: float
    safety_risk_changes: list[str]


class EvaluationCase(BaseModel):
    case_id: str
    title: str
    category: str
    user_role: Role
    user_input: str
    actor_id: str | None = None
    target_object: str | None = None
    available_tools: list[str]
    injected_fault: dict[str, Any] | None = None
    expected_tool: str | None = None
    expected_arguments: dict[str, Any] = Field(default_factory=dict)
    forbidden_tools: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False
    expected_policy_decisions: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    expected_refusal: bool = False
    risk_tags: list[str] = Field(default_factory=list)
    severity: str
    description: str
    confirm_second_factor: bool = False
    human_approval_id: str | None = None
    idempotency_key: str | None = None


class CaseResult(BaseModel):
    case_id: str
    title: str
    category: str
    passed: bool
    success: bool
    selected_tools: list[str]
    reasons: list[str]
    deterministic_assertions: dict[str, bool]
    heuristic_scores: dict[str, float]
    latency_ms: float
    risk_tags: list[str]
    trace_id: str


class QualityGate(BaseModel):
    status: Literal["PASS", "FAIL"]
    hard_failures: list[str]
    soft_failures: list[str]
    thresholds: dict[str, float]


class EvaluationRun(BaseModel):
    run_id: str
    created_at: datetime = Field(default_factory=utc_now)
    dataset_version: str
    provider: str
    prompt_version: str
    policy_version: str
    metrics: dict[str, float]
    quality_gate: QualityGate
    results: list[CaseResult]


class CompareRequest(BaseModel):
    baseline_run_id: str
    candidate_run_id: str


class EvaluationComparison(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    metric_deltas: dict[str, float]
    new_failures: list[str]
    recovered_cases: list[str]
    regression_count: int
    high_risk_regression_count: int

