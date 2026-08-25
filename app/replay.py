from __future__ import annotations

import uuid

from .errors import AppError
from .models import ReplayComparison, ReplayRequest, ToolEvent, TraceRecord
from .storage import Store


class ReplayEngine:
    """Offline replay uses saved, already-redacted tool responses and never repeats writes."""

    def __init__(self, store: Store):
        self.store = store

    def replay(self, trace_id: str, request: ReplayRequest) -> tuple[TraceRecord, ReplayComparison]:
        original = self.store.get_trace(trace_id)
        if not original:
            raise AppError(404, "trace_not_found", "Trace 不存在。")
        replayed_events = [event.model_copy(update={"status": "replayed", "side_effect": False}) for event in original.tool_events]
        replayed = original.model_copy(update={
            "trace_id": f"trace-{uuid.uuid4().hex[:12]}",
            "request_id": f"replay-{uuid.uuid4().hex[:10]}",
            "provider": request.provider or original.provider,
            "prompt_version": request.prompt_version or original.prompt_version,
            "policy_version": request.policy_version or original.policy_version,
            "tool_events": replayed_events,
            "replay_of": original.trace_id,
            "decision": f"offline_replay:{request.mode}",
        })
        self.store.save_trace(replayed)
        return replayed, self.compare(original, replayed)

    @staticmethod
    def compare(baseline: TraceRecord, candidate: TraceRecord) -> ReplayComparison:
        base_tools = [event.tool_name for event in baseline.tool_events]
        candidate_tools = [event.tool_name for event in candidate.tool_events]
        tool_changes = [] if base_tools == candidate_tools else [f"{base_tools} -> {candidate_tools}"]
        base_args = [event.arguments for event in baseline.tool_events]
        candidate_args = [event.arguments for event in candidate.tool_events]
        policy_base = [(item.policy_id, item.decision) for item in baseline.policy_decisions]
        policy_candidate = [(item.policy_id, item.decision) for item in candidate.policy_decisions]
        return ReplayComparison(
            baseline_trace_id=baseline.trace_id,
            candidate_trace_id=candidate.trace_id,
            tool_selection_changes=tool_changes,
            argument_changes=[] if base_args == candidate_args else ["saved arguments differ"],
            policy_changes=[] if policy_base == policy_candidate else ["policy decision sequence differs"],
            new_failures=[] if baseline.success or candidate.success else [candidate.trace_id],
            recovered_cases=[candidate.trace_id] if not baseline.success and candidate.success else [],
            latency_delta_ms=round(candidate.total_duration_ms - baseline.total_duration_ms, 2),
            cost_delta_usd=round(candidate.estimated_cost_usd - baseline.estimated_cost_usd, 6),
            safety_risk_changes=sorted(set(candidate.risk_tags).symmetric_difference(baseline.risk_tags)),
        )

