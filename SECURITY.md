# Security Policy

AgentGuard AI is an educational, fictional sandbox. It must never be connected directly to a real bank, payment, identity, credit, SMS, or production customer system.

## Reporting a vulnerability

Please open a private GitHub security advisory instead of a public issue when the report contains an exploitable security weakness. Do not include real credentials or personal data. A maintainer should acknowledge the report within seven days; this is a project policy, not an SLA.

## Credential rules

- The default Provider is offline and needs no secret.
- The optional OpenAI Provider reads `OPENAI_API_KEY` from the process environment only.
- `.env`, SQLite databases, logs, coverage output, and downloaded dependencies are ignored.
- All committed people, banks, IDs, accounts, transactions, phones, and emails are synthetic regression fixtures.

Supported branch: the latest `main` branch after the repository is published.

