# Contributing

1. Fork the repository and create a focused branch.
2. Use Python 3.11+ and install `pip install -e ".[dev]"`.
3. Add or update tests for every behavior change. Do not lower a safety gate to make a failing case pass.
4. Use only fictional data. Never place credentials, personal data, production endpoints, or private logs in an issue or pull request.
5. Run `pytest tests/test_unit.py tests/test_api.py`, `pytest tests/test_ui.py -m ui`, and `python scripts/run_quality_gate.py`.
6. Explain whether a test fixture is an injected defect, training exercise, regression fixture, or an actual defect found during development.

Commits should be small and descriptive. This local delivery intentionally contains no commit made on behalf of the project owner.

