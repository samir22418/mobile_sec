from __future__ import annotations

import json

from app.config import Settings
from app.shieldy.fast_router import route_request
from app.shieldy.models import ShieldyModelRegistry
from app.shieldy.prompts import build_system_prompt
from app.shieldy.providers import ShieldyProvider
from app.shieldy.security_gate import evaluate_request
from app.shieldy.state import ShieldyTurnRequest, ShieldyTurnResponse

ALLOWED_ACTION_TOOLS = {"create_analyst_feedback", "create_review_note"}


class ShieldyAgent:
    def __init__(self, settings: Settings, provider: ShieldyProvider) -> None:
        self.settings = settings
        self.provider = provider
        self.models = ShieldyModelRegistry.from_settings(settings)

    def run_turn(self, request: ShieldyTurnRequest) -> ShieldyTurnResponse:
        latest_user = latest_user_message(request.messages)
        safety = evaluate_request(latest_user)
        route = route_request(latest_user, has_context=bool(request.context))
        model = self.models.model_for_route(route)
        safety_dict = {
            "action": safety.action,
            "risk_level": safety.risk_level,
            "reason": safety.reason,
        }
        if safety.action == "refuse":
            return ShieldyTurnResponse(
                answer=safety.user_message,
                actions=[],
                route=route.route,
                safety=safety_dict,
                model_name=model,
            )

        messages = [{"role": "system", "content": build_system_prompt(route, safety)}]
        messages.extend(request.messages)
        if request.context:
            context_json = json.dumps(request.context, sort_keys=True)
            messages.append({"role": "user", "content": f"Selected redacted AEGIS context JSON: {context_json}"})

        decoded = self.provider.complete_json(
            model=model,
            messages=messages,
            timeout=self.settings.openrouter_timeout_seconds,
        )
        actions = sanitize_actions(decoded.get("actions", []))
        raw_safety = decoded.get("safety")
        safety_out: dict = raw_safety if isinstance(raw_safety, dict) else safety_dict
        return ShieldyTurnResponse(
            answer=str(decoded.get("answer", "")),
            actions=actions,
            route=str(decoded.get("route") or route.route),
            safety=safety_out,
            model_name=model,
        )


def latest_user_message(messages: list[dict]) -> str:
    return next((str(message.get("content", "")) for message in reversed(messages) if message.get("role") == "user"), "")


def sanitize_actions(actions: object) -> list[dict]:
    if not isinstance(actions, list):
        return []
    safe_actions = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        tool_name = action.get("tool_name")
        if tool_name not in ALLOWED_ACTION_TOOLS:
            continue
        payload = action.get("payload")
        safe_actions.append({"tool_name": tool_name, "payload": payload if isinstance(payload, dict) else {}})
    return safe_actions
