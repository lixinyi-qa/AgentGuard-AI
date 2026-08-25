from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, Settings
from .errors import AppError
from .evaluation import EvaluationEngine
from .faults import FaultInjectionEngine
from .models import AgentRunRequest, CompareRequest, FaultCreate, ReplayRequest
from .policies import POLICY_CATALOG
from .replay import ReplayEngine
from .reporting import html_report, json_report
from .retrieval import KnowledgeBase
from .runtime import AgentRuntime
from .storage import Store
from .tools import TOOL_CONTRACTS, ToolSandbox


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings(database_url=database_url) if database_url else Settings()
    store = Store(settings.database_url)
    knowledge = KnowledgeBase(ROOT / "data" / "knowledge")
    faults = FaultInjectionEngine(store)
    sandbox = ToolSandbox(store, knowledge, faults)
    runtime = AgentRuntime(settings, store, knowledge, sandbox)
    replay_engine = ReplayEngine(store)
    evaluation = EvaluationEngine(runtime, faults, store, ROOT / "data" / "evaluation_cases.json")

    app = FastAPI(
        title="AgentGuard AI",
        description="Digital-twin quality assurance platform for AI agents — fictional sandbox only",
        version="1.0.0",
    )
    app.state.services = {"settings": settings, "store": store, "faults": faults, "runtime": runtime, "replay": replay_engine, "evaluation": evaluation}
    app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "request_id": request.state.request_id}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = sorted({".".join(str(part) for part in error["loc"] if part != "body") for error in exc.errors()})
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": f"请求参数校验失败：{', '.join(fields)}", "request_id": request.state.request_id}})

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "请求的资源不存在。", "request_id": request.state.request_id}})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        store.audit(request.state.request_id, "internal_error", {"type": type(exc).__name__})
        return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "服务处理失败，未暴露内部路径、堆栈或凭据。", "request_id": request.state.request_id}})

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def dashboard():
        return (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")

    @app.get("/health")
    def health(request: Request):
        return {"request_id": request.state.request_id, "status": "ok", "provider": settings.provider, "dataset_version": evaluation.dataset_version, "sandbox": "fictional-only"}

    @app.get("/api/tools")
    def list_tools(request: Request):
        return {"request_id": request.state.request_id, "items": [tool.model_dump(mode="json") for tool in TOOL_CONTRACTS]}

    @app.get("/api/policies")
    def list_policies(request: Request):
        return {"request_id": request.state.request_id, "version": settings.policy_version, "items": POLICY_CATALOG}

    @app.post("/api/agent/run")
    def run_agent(payload: AgentRunRequest, request: Request):
        return runtime.run(payload, request.state.request_id)

    @app.get("/api/traces")
    def list_traces(request: Request, limit: int = 50):
        traces = store.list_traces(min(max(limit, 1), 100))
        return {"request_id": request.state.request_id, "items": [trace.model_dump(mode="json") for trace in traces]}

    @app.get("/api/traces/{trace_id}")
    def get_trace(trace_id: str, request: Request):
        trace = store.get_trace(trace_id)
        if not trace:
            raise AppError(404, "trace_not_found", "Trace 不存在。")
        return {"request_id": request.state.request_id, "trace": trace.model_dump(mode="json")}

    @app.post("/api/traces/{trace_id}/replay")
    def replay_trace(trace_id: str, payload: ReplayRequest, request: Request):
        replayed, comparison = replay_engine.replay(trace_id, payload)
        return {"request_id": request.state.request_id, "trace": replayed.model_dump(mode="json"), "comparison": comparison.model_dump(mode="json")}

    @app.post("/api/faults", status_code=201)
    def create_fault(payload: FaultCreate, request: Request):
        if payload.target_tool not in {tool.name for tool in TOOL_CONTRACTS}:
            raise AppError(422, "unknown_tool", "故障目标工具不存在。")
        fault = faults.create(payload)
        return {"request_id": request.state.request_id, "fault": fault.model_dump(mode="json")}

    @app.get("/api/faults")
    def list_faults(request: Request):
        return {"request_id": request.state.request_id, "items": [fault.model_dump(mode="json") for fault in store.list_faults()]}

    @app.delete("/api/faults/{fault_id}")
    def delete_fault(fault_id: str, request: Request):
        if not store.delete_fault(fault_id):
            raise AppError(404, "fault_not_found", "故障配置不存在。")
        return {"request_id": request.state.request_id, "deleted": True, "fault_id": fault_id}

    @app.post("/api/evaluations/run", status_code=201)
    def run_evaluation(request: Request):
        run = evaluation.run()
        return {"request_id": request.state.request_id, "run": run.model_dump(mode="json")}

    @app.get("/api/evaluations/runs")
    def list_evaluations(request: Request):
        return {"request_id": request.state.request_id, "items": [run.model_dump(mode="json") for run in store.list_evaluations()]}

    @app.get("/api/evaluations/runs/{run_id}")
    def get_evaluation(run_id: str, request: Request):
        run = store.get_evaluation(run_id)
        if not run:
            raise AppError(404, "evaluation_not_found", "评测运行不存在。")
        return {"request_id": request.state.request_id, "run": run.model_dump(mode="json")}

    @app.post("/api/evaluations/compare")
    def compare_evaluations(payload: CompareRequest, request: Request):
        result = evaluation.compare(payload.baseline_run_id, payload.candidate_run_id)
        return {"request_id": request.state.request_id, "comparison": result.model_dump(mode="json")}

    @app.get("/api/reports/{run_id}.json")
    def report_json(run_id: str):
        run = store.get_evaluation(run_id)
        if not run:
            raise AppError(404, "evaluation_not_found", "评测运行不存在。")
        return HTMLResponse(json_report(run), media_type="application/json", headers={"Content-Disposition": f"attachment; filename={run_id}.json"})

    @app.get("/api/reports/{run_id}.html")
    def report_html(run_id: str):
        run = store.get_evaluation(run_id)
        if not run:
            raise AppError(404, "evaluation_not_found", "评测运行不存在。")
        return HTMLResponse(html_report(run), headers={"Content-Disposition": f"attachment; filename={run_id}.html"})

    return app


app = create_app()

