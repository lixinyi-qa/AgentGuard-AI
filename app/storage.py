from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from .models import EvaluationRun, FaultRecord, TraceRecord


class Base(DeclarativeBase):
    pass


class JsonRecordMixin:
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TraceRow(JsonRecordMixin, Base):
    __tablename__ = "traces"
    trace_id: Mapped[str] = mapped_column(String(64), primary_key=True)


class EvaluationRow(JsonRecordMixin, Base):
    __tablename__ = "evaluation_runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)


class FaultRow(JsonRecordMixin, Base):
    __tablename__ = "faults"
    fault_id: Mapped[str] = mapped_column(String(64), primary_key=True)


class IdempotencyRow(Base):
    __tablename__ = "idempotency_records"
    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    tool_name: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditRow(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    detail_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Store:
    def __init__(self, database_url: str):
        kwargs: dict[str, Any] = {"future": True}
        if database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
        self.engine = create_engine(database_url, **kwargs)
        Base.metadata.create_all(self.engine)

    @staticmethod
    def _dump(model: Any) -> str:
        return json.dumps(model.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))

    def save_trace(self, trace: TraceRecord) -> None:
        with Session(self.engine) as session:
            session.merge(TraceRow(trace_id=trace.trace_id, payload=self._dump(trace)))
            session.commit()

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        with Session(self.engine) as session:
            row = session.get(TraceRow, trace_id)
            return TraceRecord.model_validate_json(row.payload) if row else None

    def list_traces(self, limit: int = 50) -> list[TraceRecord]:
        with Session(self.engine) as session:
            rows = session.scalars(select(TraceRow).order_by(TraceRow.created_at.desc()).limit(limit)).all()
            return [TraceRecord.model_validate_json(row.payload) for row in rows]

    def save_evaluation(self, run: EvaluationRun) -> None:
        with Session(self.engine) as session:
            session.merge(EvaluationRow(run_id=run.run_id, payload=self._dump(run)))
            session.commit()

    def get_evaluation(self, run_id: str) -> EvaluationRun | None:
        with Session(self.engine) as session:
            row = session.get(EvaluationRow, run_id)
            return EvaluationRun.model_validate_json(row.payload) if row else None

    def list_evaluations(self, limit: int = 30) -> list[EvaluationRun]:
        with Session(self.engine) as session:
            rows = session.scalars(select(EvaluationRow).order_by(EvaluationRow.created_at.desc()).limit(limit)).all()
            return [EvaluationRun.model_validate_json(row.payload) for row in rows]

    def save_fault(self, fault: FaultRecord) -> None:
        with Session(self.engine) as session:
            session.merge(FaultRow(fault_id=fault.fault_id, payload=self._dump(fault)))
            session.commit()

    def get_fault(self, fault_id: str) -> FaultRecord | None:
        with Session(self.engine) as session:
            row = session.get(FaultRow, fault_id)
            return FaultRecord.model_validate_json(row.payload) if row else None

    def list_faults(self) -> list[FaultRecord]:
        with Session(self.engine) as session:
            rows = session.scalars(select(FaultRow).order_by(FaultRow.created_at.desc())).all()
            return [FaultRecord.model_validate_json(row.payload) for row in rows]

    def delete_fault(self, fault_id: str) -> bool:
        with Session(self.engine) as session:
            row = session.get(FaultRow, fault_id)
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True

    def consume_fault(self, fault_id: str) -> FaultRecord | None:
        fault = self.get_fault(fault_id)
        if not fault or not fault.enabled or fault.remaining_count <= 0:
            return None
        updated = fault.model_copy(update={"remaining_count": fault.remaining_count - 1})
        self.save_fault(updated)
        return fault

    def get_idempotency(self, key: str) -> tuple[str, str, dict[str, Any]] | None:
        with Session(self.engine) as session:
            row = session.get(IdempotencyRow, key)
            return (row.tool_name, row.payload_hash, json.loads(row.response_json)) if row else None

    def save_idempotency(self, key: str, tool: str, payload_hash: str, response: dict[str, Any]) -> None:
        with Session(self.engine) as session:
            session.add(IdempotencyRow(key=key, tool_name=tool, payload_hash=payload_hash, response_json=json.dumps(response, ensure_ascii=False)))
            session.commit()

    def audit(self, request_id: str, event_type: str, detail: dict[str, Any]) -> None:
        with Session(self.engine) as session:
            session.add(AuditRow(request_id=request_id, event_type=event_type, detail_json=json.dumps(detail, ensure_ascii=False, default=str)))
            session.commit()

