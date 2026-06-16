import os
from typing import Any

import requests


class AegisClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("AEGIS_API_URL", "http://127.0.0.1:8080/api/v1").rstrip("/")
        self.token = os.getenv("AEGIS_ANALYST_TOKEN", "sample-token")
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def get_devices(self) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/devices", timeout=10)
        response.raise_for_status()
        return response.json().get("items", [])

    def get_device_latest_risk(self, device_id: str) -> dict[str, Any] | None:
        response = self.session.get(f"{self.base_url}/devices/{device_id}/latest-risk", timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def get_device_timeline(self, device_id: str) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/devices/{device_id}/timeline", timeout=10)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json().get("items", [])

    def get_payload(self, payload_id: str) -> dict[str, Any] | None:
        response = self.session.get(f"{self.base_url}/payloads/{payload_id}", timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def get_logs_analysis(
        self,
        device_id: str | None = None,
        *,
        level: str | None = None,
        matched_rule: str | None = None,
        q: str | None = None,
        limit: int = 80,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if device_id:
            params["device_id"] = device_id
        if level:
            params["level"] = level
        if matched_rule:
            params["matched_rule"] = matched_rule
        if q:
            params["q"] = q
        response = self.session.get(f"{self.base_url}/logs/analysis", params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def submit_feedback(
        self,
        finding_id: str,
        label: str,
        notes: str,
        payload_id: str | None = None,
    ) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/findings/{finding_id}/feedback",
            json={"payload_id": payload_id, "label": label, "notes": notes},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_ai_runs(
        self,
        device_id: str | None = None,
        payload_id: str | None = None,
        role: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if device_id:
            params["device_id"] = device_id
        if payload_id:
            params["payload_id"] = payload_id
        if role:
            params["role"] = role
        response = self.session.get(f"{self.base_url}/ai/runs", params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("items", [])

    def get_ai_decision(self, payload_id: str) -> dict[str, Any] | None:
        response = self.session.get(f"{self.base_url}/ai/decisions/{payload_id}", timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def create_chat_session(self, title: str = "AEGIS AI chat") -> dict[str, Any]:
        response = self.session.post(f"{self.base_url}/chat/sessions", json={"title": title}, timeout=10)
        response.raise_for_status()
        return response.json()

    def send_chat_message(
        self,
        session_id: str,
        content: str,
        context_payload_id: str | None = None,
    ) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/chat/sessions/{session_id}/messages",
            json={"content": content, "context_payload_id": context_payload_id},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def confirm_chat_action(self, action_id: str) -> dict[str, Any]:
        response = self.session.post(f"{self.base_url}/chat/actions/{action_id}/confirm", timeout=10)
        response.raise_for_status()
        return response.json()


client = AegisClient()
