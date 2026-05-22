from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


class TelemetryValidationService:
    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)

    def validate(self, payload: dict) -> None:
        self.validator.validate(payload)


def validation_error_message(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    prefix = f"{path}: " if path else ""
    return f"{prefix}{error.message}"

