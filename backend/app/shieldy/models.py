from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.shieldy.state import RouteDecision


@dataclass(frozen=True)
class ShieldyModelRegistry:
    orchestrator: str
    critic: str
    general: str
    report: str
    command: str
    fast: str
    fallback: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "ShieldyModelRegistry":
        return cls(
            orchestrator=settings.openrouter_orchestrator_model,
            critic=settings.openrouter_critic_model,
            general=settings.openrouter_general_model,
            report=settings.openrouter_report_model,
            command=settings.openrouter_command_model,
            fast=settings.openrouter_fast_model,
            fallback=settings.openrouter_model,
        )

    def model_for_route(self, route: RouteDecision) -> str:
        role_to_model = {
            "orchestrator": self.orchestrator,
            "critic": self.critic,
            "general": self.general,
            "report": self.report,
            "command": self.command,
            "fast": self.fast,
        }
        return role_to_model.get(route.model_role, self.fallback)
