# AgentGuard AI

AgentGuard AI is a reproducible quality-assurance platform for tool-using AI agents. It combines a fictional banking digital twin, executable authorization policies, fault injection, redacted traces, offline replay, a 40-case evaluation set, and a CI quality gate.

This is not a chatbot demo. It tests whether an agent selects the right tool and arguments, respects role and object ownership, requests approval before high-risk actions, avoids PII leakage, rejects direct and indirect prompt injection, recovers safely from dependency faults, and produces auditable evidence.

![Dashboard](docs/assets/dashboard.png)

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The default deterministic Provider is offline and requires no API key. The optional OpenAI-compatible Provider uses the official Python SDK and Responses API; `OPENAI_API_KEY` is read only from the environment.

## Architecture and features

- Seven fictional tools with input/output schemas, roles, risk, approval, idempotency, timeout, errors, data scope, and redaction contracts.
- Twelve executable policies including object-level authorization, revoked grants, second-factor confirmation, high-value refund approval, output validation, and mandatory audit evidence.
- Fifteen fault types with retry-limit, duplicate-write, safe-degradation, and unsafe-side-effect evidence.
- A knowledge base that deliberately contains indirect prompt-injection fixtures while treating retrieved text as untrusted data.
- SQLite trace/run history, deterministic offline replay, baseline/candidate comparison, 18 core metrics, HTML/JSON reports, and GitHub Actions evidence upload.
- Responsive, keyboard-accessible dashboard with loading, empty, success, failure, and API-unavailable feedback.

![Architecture](docs/assets/architecture.svg)

## Verified local results — 2026-08-25

| Check | Actual result |
|---|---:|
| Unit + API | 41 passed, 0 failed, 0 skipped |
| Playwright UI | 6 passed, 0 failed, 0 skipped |
| Coverage of `app` from unit/API suite | 96% |
| Agent evaluation | 40/40 passed |
| Quality Gate | PASS |
| PII leaks | 0 |
| Newman | 11 requests and 11 assertions, 0 failed |
| Locust local baseline | 335 requests, 0 failed, ~37.47 req/s, aggregate P95 ~83 ms |

These are local measurements, not production capacity or regulatory certification. Groundedness is a heuristic score, not absolute factual accuracy. Docker, PostgreSQL, a live model, and remote GitHub Actions were not executed in this environment.

## Test commands

```bash
pytest tests/test_unit.py tests/test_api.py --cov=app --cov-report=html
pytest tests/test_ui.py -m ui
python scripts/run_quality_gate.py
python scripts/performance_baseline.py
npm install && npm run test:postman   # with the API running on port 8000
```

## Safety and truthfulness

Every person, bank, account, transaction, identity number, contact value, policy, approval, and refund in the repository is synthetic. The project does not connect to real financial systems and does not claim production readiness, regulatory approval, or external security certification. See [SECURITY.md](SECURITY.md), the [threat model](docs/threat-model.md), and the [evaluation methodology](docs/evaluation-methodology.md).

Suggested public repository: `lixinyi-qa/AgentGuard-AI`. No commit or remote repository was created on behalf of the owner.

