from __future__ import annotations

import uuid

from .errors import ToolFailure
from .models import FaultCreate, FaultRecord
from .storage import Store


class FaultInjectionEngine:
    def __init__(self, store: Store):
        self.store = store

    def create(self, payload: FaultCreate) -> FaultRecord:
        fault = FaultRecord(fault_id=f"fault-{uuid.uuid4().hex[:10]}", remaining_count=payload.trigger_count, **payload.model_dump())
        self.store.save_fault(fault)
        return fault

    def active_for(self, tool_name: str) -> FaultRecord | None:
        return next((fault for fault in self.store.list_faults() if fault.enabled and fault.remaining_count > 0 and fault.target_tool == tool_name), None)

    def inject(self, tool_name: str) -> str | None:
        active = self.active_for(tool_name)
        if not active:
            return None
        consumed = self.store.consume_fault(active.fault_id)
        if not consumed:
            return None
        fault_type = consumed.fault_type
        if fault_type == "timeout":
            raise ToolFailure("timeout", retryable=True)
        if fault_type in {"http_500", "http_429"}:
            raise ToolFailure(fault_type, retryable=True)
        if fault_type in {"database_unavailable", "permission_service_unavailable", "idempotency_conflict"}:
            raise ToolFailure(fault_type, retryable=False)
        return fault_type

