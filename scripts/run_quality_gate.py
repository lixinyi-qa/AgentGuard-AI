from __future__ import annotations

from pathlib import Path

from app.config import ROOT
from app.evaluation import EvaluationEngine
from app.faults import FaultInjectionEngine
from app.reporting import html_report, json_report
from app.retrieval import KnowledgeBase
from app.runtime import AgentRuntime
from app.storage import Store
from app.tools import ToolSandbox
from app.config import Settings


reports = ROOT / "reports"
reports.mkdir(exist_ok=True)
store = Store("sqlite://")
settings = Settings(database_url="sqlite://")
knowledge = KnowledgeBase(ROOT / "data" / "knowledge")
faults = FaultInjectionEngine(store)
runtime = AgentRuntime(settings, store, knowledge, ToolSandbox(store, knowledge, faults))
engine = EvaluationEngine(runtime, faults, store, ROOT / "data" / "evaluation_cases.json")
run = engine.run()
(reports / "evaluation-latest.json").write_text(json_report(run), encoding="utf-8")
(reports / "evaluation-latest.html").write_text(html_report(run), encoding="utf-8")
print(f"{run.run_id}: {run.quality_gate.status}; {sum(item.passed for item in run.results)}/{len(run.results)} cases passed")
raise SystemExit(0 if run.quality_gate.status == "PASS" else 1)

