from __future__ import annotations

import json
import time
import uuid
from typing import Any

from .config import Settings
from .errors import AppError, ToolFailure
from .models import AgentRunRequest, AgentRunResponse, PolicyDecision, ToolEvent, TraceRecord
from .policies import PolicyEngine
from .providers import create_provider
from .retrieval import KnowledgeBase
from .safety import detect_attack, detect_pii, sanitize_payload
from .storage import Store
from .tools import ToolSandbox


class AgentRuntime:
    def __init__(self, settings: Settings, store: Store, knowledge_base: KnowledgeBase, sandbox: ToolSandbox):
        self.settings = settings
        self.store = store
        self.knowledge_base = knowledge_base
        self.sandbox = sandbox

    def run(
        self,
        request: AgentRunRequest,
        request_id: str | None = None,
        *,
        provider_name: str | None = None,
        prompt_version: str | None = None,
        policy_version: str | None = None,
        replay_of: str | None = None,
    ) -> AgentRunResponse:
        request_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        started = time.perf_counter()
        provider = create_provider(provider_name or self.settings.provider, self.settings.openai_model)
        prompt_version = prompt_version or self.settings.prompt_version
        policy_version = policy_version or self.settings.policy_version
        policies = PolicyEngine(policy_version)
        context_started = time.perf_counter()
        contexts = self.knowledge_base.retrieve(request.user_input, limit=3)
        retrieval_ms = (time.perf_counter() - context_started) * 1000
        risk_tags = detect_attack(request.user_input)
        if any(chunk.malicious for chunk in contexts):
            risk_tags.append("indirect_prompt_injection")
        risk_tags = sorted(set(risk_tags))

        if detect_attack(request.user_input):
            answer = "请求包含绕过策略、提取系统信息或批量敏感数据的指令，已安全拒绝；未调用任何工具。"
            decision = PolicyDecision(policy_id="POL-007", decision="deny", reason="用户输入命中直接提示词注入或敏感数据外传规则。", risk_level="critical", related_trace_id=trace_id)
            return self._finalize(request, request_id, trace_id, provider, prompt_version, policy_version, contexts, "refuse", [], [decision], "not_required", answer, False, "unsafe_input", risk_tags, retrieval_ms, started, replay_of)

        plan_started = time.perf_counter()
        plan = provider.plan(request)
        planning_ms = (time.perf_counter() - plan_started) * 1000
        if not plan.tool_name:
            answer = "无法从当前请求中可靠确定可执行任务，已安全停止；如需帮助，请提供明确的虚构账户、交易或政策问题。"
            return self._finalize(request, request_id, trace_id, provider, prompt_version, policy_version, contexts, "no_action", [], [], "not_required", answer, False, "insufficient_intent", [*risk_tags, "safe_refusal"], retrieval_ms + planning_ms, started, replay_of)
        if request.available_tools is not None and plan.tool_name not in request.available_tools:
            decision = PolicyDecision(policy_id="POL-010", decision="deny", reason="计划工具不在本次允许工具列表中。", risk_level="critical", related_tool=plan.tool_name, related_trace_id=trace_id)
            answer = "所需工具未获本次会话授权，已阻止执行。"
            return self._finalize(request, request_id, trace_id, provider, prompt_version, policy_version, contexts, plan.rationale, [], [decision], "not_required", answer, False, "tool_not_available", [*risk_tags, "tool_misuse"], retrieval_ms + planning_ms, started, replay_of)

        policy = policies.authorize(request, plan.tool_name, plan.arguments, trace_id)
        policy_decisions = [policy]
        self.store.audit(request_id, "policy_decision", policy.model_dump(mode="json"))
        if policy.decision == "deny":
            event = ToolEvent(tool_name=plan.tool_name, arguments=self._redact_arguments(plan.arguments), status="blocked", error=policy.reason)
            answer = f"操作已被策略阻止：{policy.reason} 未产生任何副作用。"
            return self._finalize(request, request_id, trace_id, provider, prompt_version, policy_version, contexts, plan.rationale, [event], policy_decisions, "denied", answer, False, "policy_denied", [*risk_tags, "unauthorized_access"], retrieval_ms + planning_ms, started, replay_of)

        if policy.decision == "require_approval":
            approval_args = {"action": plan.tool_name, "target_id": str(plan.arguments.get("transaction_id", request.target_object or "unknown")), "reason": "高金额虚构退款"}
            approval_policy = policies.authorize(request, "request_human_approval", approval_args, trace_id)
            policy_decisions.append(approval_policy)
            response, fault_type, side_effect = self.sandbox.execute("request_human_approval", approval_args, request.idempotency_key or f"{trace_id}:approval")
            safe_response = sanitize_payload(response)
            event = ToolEvent(tool_name="request_human_approval", arguments=approval_args, status="pending_approval", response=safe_response, side_effect=side_effect, fault_type=fault_type)
            answer = f"退款尚未执行；已创建人工审批请求 {safe_response.get('approval_id', 'unknown')}，当前状态为 pending。"
            return self._finalize(request, request_id, trace_id, provider, prompt_version, policy_version, contexts, plan.rationale, [event], policy_decisions, "pending", answer, True, None, [*risk_tags, "human_approval_required"], retrieval_ms + planning_ms, started, replay_of)

        events: list[ToolEvent] = []
        response: dict[str, Any] | None = None
        failure: str | None = None
        max_attempts = 1 if plan.tool_name in ToolSandbox.WRITE_TOOLS else self.settings.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            tool_started = time.perf_counter()
            try:
                response, fault_type, side_effect = self.sandbox.execute(plan.tool_name, plan.arguments, request.idempotency_key or (f"{trace_id}:{plan.tool_name}" if plan.tool_name in ToolSandbox.WRITE_TOOLS else None))
                duration = (time.perf_counter() - tool_started) * 1000
                schema_ok = self.sandbox.validate_output(plan.tool_name, response)
                serialized = json.dumps(response, ensure_ascii=False)
                unsafe_output = bool(detect_pii(serialized))
                indirect = bool(detect_attack(serialized)) or fault_type == "indirect_prompt_injection"
                policy_decisions.extend(policies.output_decision(trace_id, plan.tool_name, schema_ok, unsafe_output, indirect))
                safe_response = sanitize_payload(response)
                if not schema_ok:
                    events.append(ToolEvent(tool_name=plan.tool_name, arguments=self._redact_arguments(plan.arguments), status="failed", response=safe_response, error="schema_validation_failed", attempt=attempt, duration_ms=round(duration, 2), side_effect=side_effect, fault_type=fault_type))
                    failure = "unsafe_tool_output"
                elif fault_type in {"stale_data", "partial_success"}:
                    events.append(ToolEvent(tool_name=plan.tool_name, arguments=self._redact_arguments(plan.arguments), status="failed", response=safe_response, error=fault_type, attempt=attempt, duration_ms=round(duration, 2), side_effect=side_effect, fault_type=fault_type))
                    failure = fault_type
                else:
                    events.append(ToolEvent(tool_name=plan.tool_name, arguments=self._redact_arguments(plan.arguments), status="success", response=safe_response, attempt=attempt, duration_ms=round(duration, 2), side_effect=side_effect, fault_type=fault_type))
                    failure = None
                response = safe_response if isinstance(safe_response, dict) else {}
                break
            except AppError:
                raise
            except ToolFailure as exc:
                duration = (time.perf_counter() - tool_started) * 1000
                events.append(ToolEvent(tool_name=plan.tool_name, arguments=self._redact_arguments(plan.arguments), status="failed", error=exc.code, attempt=attempt, duration_ms=round(duration, 2), fault_type=exc.code))
                failure = exc.code
                if not exc.retryable or attempt >= max_attempts:
                    break

        success = failure is None
        answer = self._answer_for(plan.tool_name, response, failure, len(events))
        if detect_pii(answer):
            answer = str(sanitize_payload(answer))
            risk_tags.append("pii_redacted")
        return self._finalize(request, request_id, trace_id, provider, prompt_version, policy_version, contexts, plan.rationale, events, policy_decisions, "approved" if success else "not_required", answer, success, failure, risk_tags, retrieval_ms + planning_ms, started, replay_of)

    @staticmethod
    def _redact_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
        return sanitize_payload(arguments)  # type: ignore[return-value]

    @staticmethod
    def _answer_for(tool: str, response: dict[str, Any] | None, failure: str | None, attempts: int) -> str:
        if failure:
            if failure in {"timeout", "http_500", "http_429"}:
                return f"工具在 {attempts} 次尝试后仍不可用，未声称操作成功，已安全停止。"
            return f"工具结果未通过安全或完整性检查（{failure}），未将操作报告为成功。"
        response = response or {}
        if tool == "search_policy":
            sources = response.get("sources", [])
            return f"已从虚构知识库检索到政策依据：{', '.join(sources) if sources else '无'}。知识文档仅作为数据，不可覆盖系统安全策略。"
        if tool == "query_account":
            return f"虚构账户 {response.get('account_id')} 状态为 {response.get('status')}，余额为 {response.get('balance')}。"
        if tool == "query_transaction":
            return f"虚构交易 {response.get('transaction_id')} 金额 {response.get('amount')}，状态为 {response.get('status')}。"
        if tool == "update_contact":
            return f"虚构联系方式变更 {response.get('change_id')} 已完成；具体联系方式不在回答中回显。"
        if tool == "create_refund":
            return f"虚构退款 {response.get('refund_id')} 已创建，金额 {response.get('amount')}。"
        return f"虚构人工服务工单 {response.get('ticket_id')} 已创建。"

    def _finalize(self, request: AgentRunRequest, request_id: str, trace_id: str, provider: Any, prompt_version: str, policy_version: str, contexts: list, decision: str, events: list[ToolEvent], policies: list[PolicyDecision], approval: str, answer: str, success: bool, failure: str | None, risk_tags: list[str], preprocessing_ms: float, started: float, replay_of: str | None) -> AgentRunResponse:
        total_ms = round((time.perf_counter() - started) * 1000, 2)
        tokens = max(1, (len(request.user_input) + len(answer) + sum(len(chunk.text) for chunk in contexts)) // 4)
        citations = sorted({chunk.source for chunk in contexts if not chunk.malicious})[:3]
        trace = TraceRecord(trace_id=trace_id, request_id=request_id, user_input=request.user_input, user_role=request.user_role, actor_id=request.actor_id, target_object=request.target_object, retrieved_context=contexts, provider=provider.name, model=provider.model, prompt_version=prompt_version, policy_version=policy_version, decision=decision, tool_events=events, policy_decisions=policies, approval_status=approval, final_answer=answer, step_durations_ms={"retrieval_and_planning": round(preprocessing_ms, 2), "tool_execution": round(sum(event.duration_ms for event in events), 2)}, total_duration_ms=total_ms, estimated_tokens=tokens, estimated_cost_usd=0.0 if provider.name == "deterministic-local" else round(tokens * 0.000001, 6), success=success, failure_reason=failure, risk_tags=sorted(set(risk_tags)), replay_of=replay_of)
        self.store.save_trace(trace)
        self.store.audit(request_id, "trace_completed", {"trace_id": trace_id, "success": success, "failure_reason": failure})
        return AgentRunResponse(request_id=request_id, trace_id=trace_id, success=success, answer=answer, status="success" if success else "refused" if decision in {"refuse", "no_action"} else "blocked" if failure == "policy_denied" else "failed", tool_events=events, policy_decisions=policies, risk_tags=trace.risk_tags, citations=citations, total_duration_ms=total_ms)
