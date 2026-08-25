from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("AGENTGUARD_DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'agentguard.db'}")
    provider: str = os.getenv("AGENTGUARD_PROVIDER", "deterministic-local")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    prompt_version: str = os.getenv("AGENTGUARD_PROMPT_VERSION", "v1")
    policy_version: str = os.getenv("AGENTGUARD_POLICY_VERSION", "v1")
    max_retries: int = int(os.getenv("AGENTGUARD_MAX_RETRIES", "2"))

