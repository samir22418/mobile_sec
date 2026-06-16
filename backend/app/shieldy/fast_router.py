from __future__ import annotations

import re

from app.shieldy.state import RouteDecision

EMAIL_RE = re.compile(r"[\w.\-+%]+@[\w.\-]+\.[A-Za-z]{2,}")


def find_email(text: str) -> str | None:
    match = EMAIL_RE.search(text or "")
    return match.group(0).strip(".,;:()[]{}<>") if match else None


def has_any(text: str, markers: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in markers)


def route_request(text: str, has_context: bool = False) -> RouteDecision:
    lowered = (text or "").lower()
    if has_any(lowered, ["confirm", "feedback", "true positive", "false positive", "benign", "needs more data"]):
        return RouteDecision("action_confirmation", "analyst_action_request", "orchestrator", needs_confirmation=True)
    if has_any(lowered, ["report", "summary", "summarize", "write up", "pdf", "docx", "markdown"]):
        return RouteDecision("report_artifact", "report_or_summary_request", "report")
    if has_any(lowered, ["command", "script", "code", "powershell", "bash", "python", "sql"]):
        return RouteDecision("safe_command_workflow", "defensive_command_or_code_request", "command")
    if has_context or has_any(lowered, ["payload", "device", "risk", "logs", "telemetry", "finding", "evidence"]):
        return RouteDecision("context_followup_fast", "aegis_context_question", "general")
    if has_any(lowered, ["explain", "why", "how", "what is", "what are"]):
        return RouteDecision("explanation_agent_fast", "general_explanation_request", "general")
    return RouteDecision("direct_answer", "general_security_question", "fast")
