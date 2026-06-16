from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SafetyDecision:
    action: str
    risk_level: str
    reason: str
    user_message: str = ""


@dataclass(frozen=True)
class RouteDecision:
    route: str
    reason: str
    model_role: str
    needs_confirmation: bool = False


@dataclass(frozen=True)
class ShieldyTurnRequest:
    messages: list[dict[str, Any]]
    context: dict[str, Any] | None = None


@dataclass
class ShieldyTurnResponse:
    answer: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    route: str = "direct_answer"
    safety: dict[str, Any] = field(default_factory=dict)
    model_name: str = ""
