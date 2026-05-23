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


client = AegisClient()
