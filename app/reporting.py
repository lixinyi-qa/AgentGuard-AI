from __future__ import annotations

import html
import json

from .metrics import METRIC_METHODS
from .models import EvaluationRun


def json_report(run: EvaluationRun) -> str:
    payload = run.model_dump(mode="json")
    payload["metric_methodology"] = METRIC_METHODS
    payload["truthfulness_note"] = "All figures in this report come from this recorded local run. Heuristic groundedness is not an absolute truth score."
    return json.dumps(payload, ensure_ascii=False, indent=2)


def html_report(run: EvaluationRun) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(item.case_id)}</td><td>{html.escape(item.title)}</td><td>{'PASS' if item.passed else 'FAIL'}</td><td>{html.escape(', '.join(item.reasons) or '—')}</td></tr>"
        for item in run.results
    )
    metrics = "".join(f"<li><strong>{html.escape(name)}</strong>: {value}</li>" for name, value in run.metrics.items())
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>AgentGuard AI Report {html.escape(run.run_id)}</title><style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;color:#102a43}}h1{{color:#073b4c}}.gate{{padding:12px;border-left:6px solid {'#0f766e' if run.quality_gate.status == 'PASS' else '#b42318'};background:#f0fdfa}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #cbd5e1;padding:8px;text-align:left}}th{{background:#e6fffb}}</style></head><body><h1>AgentGuard AI 评测报告</h1><p>Run: {html.escape(run.run_id)} · Dataset: {html.escape(run.dataset_version)} · Provider: {html.escape(run.provider)}</p><p class='gate'>Quality Gate: <strong>{run.quality_gate.status}</strong></p><h2>指标</h2><ul>{metrics}</ul><p>Groundedness 是启发式评分，不代表绝对真实准确率。本报告数据来自本次本机真实运行。</p><h2>案例</h2><table><thead><tr><th>ID</th><th>标题</th><th>结果</th><th>原因</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""

