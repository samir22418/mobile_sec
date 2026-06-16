from __future__ import annotations

from typing import Protocol

from app.config import Settings
from app.shieldy import ShieldyAgent
from app.shieldy.providers import OpenRouterProvider
from app.shieldy.state import ShieldyTurnRequest


class ChatAssistantProvider(Protocol):
    model_name: str
    provider_name: str

    def send(self, messages: list[dict], context: dict | None = None) -> dict:
        ...


class OpenRouterChatProvider:
    provider_name = "openrouter"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_name = settings.openrouter_model
        self.agent = ShieldyAgent(settings, OpenRouterProvider(settings))

    def send(self, messages: list[dict], context: dict | None = None) -> dict:
        result = self.agent.run_turn(ShieldyTurnRequest(messages=messages, context=context))
        self.model_name = result.model_name
        return {
            "answer": result.answer,
            "actions": result.actions,
            "route": result.route,
            "safety": result.safety,
        }
