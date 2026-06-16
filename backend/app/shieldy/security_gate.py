from __future__ import annotations

import re

from app.shieldy.state import SafetyDecision

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"forget\s+(all\s+)?(previous|prior)\s+instructions",
    r"override\s+(the\s+)?(system|developer)\s+(prompt|instructions)",
    r"reveal\s+(your\s+)?(system|developer|hidden)\s+(prompt|instructions|rules)",
    r"show\s+(me\s+)?(your\s+)?(system|developer|hidden)\s+(prompt|instructions|rules)",
    r"print\s+(your\s+)?(system|developer|hidden)\s+(prompt|instructions)",
    r"routing\s+rules.*(secret|hidden|internal)",
    r"jailbreak",
    r"developer\s+mode",
    r"act\s+as\s+dan",
]

DANGEROUS_PATTERNS = [
    r"\bsteal\b.*\b(password|token|cookie|session|credential)s?\b",
    r"\bdump\b.*\b(password|token|cookie|session|credential)s?\b",
    r"\bextract\b.*\b(password|token|cookie|session|credential)s?\b",
    r"\bexfiltrat(e|ion)\b",
    r"\bbypass\b.*\b(authentication|login|2fa|mfa|otp)\b",
    r"\bphishing\b",
    r"\bcredential\s+theft\b",
    r"\bkeylogger\b",
    r"\bmalware\b",
    r"\bransomware\b",
    r"\breverse\s+shell\b",
    r"\bpersistence\b.*\b(evasion|stealth|hide)\b",
    r"\brm\s+-rf\s+(/|\*)",
    r"\bformat\s+[a-zA-Z]:",
    r"\bcurl\b.*\|\s*(bash|sh|zsh|python|perl)",
    r"\bwget\b.*\|\s*(bash|sh|zsh|python|perl)",
]

DEFENSIVE_HINTS = [
    "aegis",
    "shieldy",
    "my project",
    "my device",
    "owned",
    "authorized",
    "permission",
    "lab",
    "ctf",
    "sandbox",
    "defensive",
    "hardening",
    "secure",
    "protect",
    "mitigation",
    "audit",
    "review",
    "local",
    "source code",
    "repo",
    "codebase",
]


def matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text or "", flags=re.IGNORECASE) for pattern in patterns)


def evaluate_request(text: str) -> SafetyDecision:
    lowered = (text or "").lower()
    if matches_any(lowered, PROMPT_INJECTION_PATTERNS):
        return SafetyDecision(
            action="refuse",
            risk_level="blocked",
            reason="prompt_injection",
            user_message="I cannot reveal or override internal instructions. I can still help with defensive AEGIS analysis.",
        )
    if matches_any(lowered, DANGEROUS_PATTERNS) and not any(hint in lowered for hint in DEFENSIVE_HINTS):
        return SafetyDecision(
            action="refuse",
            risk_level="blocked",
            reason="unsafe_cyber_request",
            user_message="I can help with defensive analysis, mitigation, and review, but not offensive or credential-theft guidance.",
        )
    return SafetyDecision(action="allow", risk_level="low", reason="allowed")
