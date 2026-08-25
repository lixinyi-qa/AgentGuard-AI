from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .models import RetrievedChunk


TOKEN_RE = re.compile(r"[a-z0-9_-]+|[\u4e00-\u9fff]", re.IGNORECASE)
MALICIOUS_MARKERS = ("忽略系统", "直接调用", "不要请求人工审批", "系统提示词", "环境变量", "send the phone")


def tokenize(text: str) -> list[str]:
    raw = TOKEN_RE.findall(text.lower())
    chinese = [token for token in raw if "\u4e00" <= token <= "\u9fff"]
    latin = [token for token in raw if token not in chinese and len(token) > 1]
    bigrams = ["".join(chinese[index:index + 2]) for index in range(len(chinese) - 1)]
    return latin + chinese + bigrams


@dataclass(frozen=True)
class KnowledgeDocument:
    source: str
    text: str
    tokens: Counter[str]
    malicious: bool


class KnowledgeBase:
    def __init__(self, directory: Path):
        self.documents = self._load(directory)
        if not self.documents:
            raise ValueError(f"No knowledge documents found in {directory}")

    @staticmethod
    def _load(directory: Path) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []
        for path in sorted(directory.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            for part in re.split(r"\n\s*\n", content):
                text = " ".join(line.strip("# -") for line in part.splitlines()).strip()
                if len(text) < 12:
                    continue
                documents.append(KnowledgeDocument(path.name, text, Counter(tokenize(text)), any(marker in text for marker in MALICIOUS_MARKERS)))
        return documents

    def retrieve(self, query: str, limit: int = 3) -> list[RetrievedChunk]:
        query_tokens = Counter(tokenize(query))
        if not query_tokens:
            return []
        frequency = {token: sum(token in doc.tokens for doc in self.documents) for token in query_tokens}
        scored: list[tuple[float, KnowledgeDocument]] = []
        for doc in self.documents:
            score = sum(
                min(count, 2) * (1 + math.log(doc.tokens.get(token, 1))) * (math.log((len(self.documents) + 1) / (frequency[token] + 0.5)) + 1)
                for token, count in query_tokens.items() if token in doc.tokens
            )
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda item: (-item[0], item[1].source, item[1].text))
        return [RetrievedChunk(source=doc.source, text=doc.text, score=round(score, 4), malicious=doc.malicious) for score, doc in scored[:limit]]

