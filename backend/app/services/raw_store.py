from __future__ import annotations

import json
import re
from pathlib import Path


class RawPayloadStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, payload_id: str, payload: dict) -> Path:
        path = self.root / f"{safe_name(payload_id)}.json"
        path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        return path

    def load(self, path: str | Path) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))


def safe_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
    return safe[:160] or "payload"

