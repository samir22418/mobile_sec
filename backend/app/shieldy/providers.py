from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Protocol

from app.config import Settings


class ChatProviderNotConfigured(RuntimeError):
    pass


class ShieldyProvider(Protocol):
    provider_name: str

    def complete_json(self, *, model: str, messages: list[dict], timeout: int) -> dict:
        ...


class OpenRouterProvider:
    provider_name = "openrouter"

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url.rstrip("/")

    def complete_json(self, *, model: str, messages: list[dict], timeout: int) -> dict:
        if not self.api_key:
            raise ChatProviderNotConfigured("OpenRouter is not configured. Set OPENROUTER_API_KEY.")
        body = json.dumps(
            {
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:8501",
                "X-Title": "AEGIS Analyst Dashboard",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise RuntimeError(f"OpenRouter request failed: {error}") from error
        content = payload["choices"][0]["message"]["content"]
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError:
            decoded = {"answer": content, "actions": []}
        return decoded if isinstance(decoded, dict) else {"answer": str(decoded), "actions": []}
