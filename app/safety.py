from __future__ import annotations

import re


ATTACK_PATTERNS: dict[str, list[str]] = {
    "direct_prompt_injection": [
        r"ignore.{0,24}(previous|prior|system|instructions?)",
        r"忽略.{0,12}(之前|以上|系统|指令|要求)",
        r"越狱|jailbreak|绕过.{0,8}(规则|策略|审批)",
    ],
    "system_prompt_extraction": [r"(reveal|show|print|输出|泄露).{0,18}(system prompt|系统提示词|隐藏指令)"],
    "sensitive_data_exfiltration": [
        r"(show|print|reveal|输出|告诉我).{0,20}(api.?key|token|password|密钥|令牌|密码|环境变量|\.env)",
        r"(全部|所有|批量).{0,12}(手机号|身份证|邮箱|客户数据|个人信息)",
    ],
    "excessive_agency": [r"(不要|无需|跳过).{0,10}(审批|确认).{0,12}(退款|修改)", r"直接.{0,8}(退款|修改手机号|修改邮箱)"],
}

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "mainland_phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "mainland_id": re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
    "api_key_like": re.compile(r"\b(?:sk|api)[-_][A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
}


def detect_attack(text: str) -> list[str]:
    return [tag for tag, patterns in ATTACK_PATTERNS.items() if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)]


def detect_pii(text: str) -> list[str]:
    return [name for name, pattern in PII_PATTERNS.items() if pattern.search(text)]


def redact_text(text: str) -> str:
    result = text
    result = PII_PATTERNS["mainland_phone"].sub(lambda m: f"{m.group(0)[:3]}****{m.group(0)[-4:]}", result)
    result = PII_PATTERNS["email"].sub(lambda m: f"{m.group(0)[0]}***@{m.group(0).split('@', 1)[1]}", result)
    result = PII_PATTERNS["mainland_id"].sub(lambda m: f"{m.group(0)[:3]}***********{m.group(0)[-4:]}", result)
    result = PII_PATTERNS["api_key_like"].sub("[REDACTED_API_KEY]", result)
    return result


def sanitize_payload(payload: object) -> object:
    if isinstance(payload, str):
        return redact_text(payload)
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {key: sanitize_payload(value) for key, value in payload.items() if key.lower() not in {"api_key", "secret", "password"}}
    return payload

