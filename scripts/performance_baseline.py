from __future__ import annotations

import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.metrics import percentile


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(create_app("sqlite://"))
ITERATIONS = 100


def sample(method: str, path: str, **kwargs):
    values = []
    failures = 0
    for _ in range(ITERATIONS):
        started = time.perf_counter()
        response = getattr(client, method)(path, **kwargs)
        values.append((time.perf_counter() - started) * 1000)
        failures += response.status_code >= 400
    return {"requests": ITERATIONS, "failures": failures, "p50_ms": percentile(values, .50), "p95_ms": percentile(values, .95), "mean_ms": round(statistics.fmean(values), 2), "requests_per_second_sequential": round(1000 / statistics.fmean(values), 2)}


results = {
    "scope": "Local sequential TestClient baseline; not production capacity",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "environment": {"python": platform.python_version(), "platform": platform.platform(), "iterations_per_endpoint": ITERATIONS},
    "endpoints": {
        "agent_read_only": sample("post", "/api/agent/run", json={"user_input": "查询虚构账户 ACC-001", "user_role": "customer", "actor_id": "CUST-001", "target_object": "ACC-001"}),
        "trace_history": sample("get", "/api/traces?limit=10"),
        "evaluation_history": sample("get", "/api/evaluations/runs"),
    },
}
(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports" / "performance-baseline.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))

