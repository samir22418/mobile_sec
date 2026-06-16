from __future__ import annotations

import hashlib
import re

SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)(token=)[^\s&]+"),
    re.compile(r"(?i)(password=)[^\s&]+"),
    re.compile(r"(?i)(secret=)[^\s&]+"),
    re.compile(r"(?i)\b((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|key)\s*[:=]\s*)[^\s&]+"),
]
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d .-]{7,}\d)(?!\d)")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class RedactionService:
    def redact(self, value: str) -> str:
        redacted = value
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub(lambda match: f"{match.group(1)}<redacted>", redacted)
        redacted = SSN_PATTERN.sub("<redacted-ssn>", redacted)
        redacted = CREDIT_CARD_PATTERN.sub("<redacted-card>", redacted)
        redacted = EMAIL_PATTERN.sub("<redacted-email>", redacted)
        redacted = PHONE_PATTERN.sub("<redacted-phone>", redacted)
        return redacted

    def hash_message(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

