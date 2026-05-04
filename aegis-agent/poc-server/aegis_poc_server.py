#!/usr/bin/env python3
"""
Tiny AEGIS telemetry POC server.

No framework, auth, database, Kafka, or production behavior. This server exists
only to validate that the Android agent can POST telemetry and exercise retry
handling with controlled failures.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


class TelemetryStore:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_path = self.output_dir / "telemetry.jsonl"

    def append(self, payload: dict[str, Any], headers: dict[str, str]) -> None:
        record = {
            "received_at_epoch_ms": int(time.time() * 1000),
            "payload_id": payload.get("payload_id"),
            "scan_id": payload.get("scan_id"),
            "device_id": payload.get("device_id"),
            "header_payload_id": headers.get("x-aegis-payload-id"),
            "header_device_id": headers.get("x-aegis-device-id"),
            "payload": payload,
        }
        with self.telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True))
            handle.write("\n")


def make_handler(store: TelemetryStore, fail_file: Path):
    class AegisPocHandler(BaseHTTPRequestHandler):
        server_version = "AegisPocServer/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self.respond_json(HTTPStatus.OK, {"ok": True, "service": "aegis-poc-server"})
                return

            if parsed.path == "/fail":
                params = parse_qs(parsed.query)
                enabled = params.get("enabled", ["true"])[0].lower() in {"1", "true", "yes", "on"}
                if enabled:
                    fail_file.write_text("1", encoding="utf-8")
                elif fail_file.exists():
                    fail_file.unlink()
                self.respond_json(HTTPStatus.OK, {"forced_failure": enabled})
                return

            self.respond_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/v1/telemetry":
                self.respond_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return

            if fail_file.exists() or self.headers.get("X-Aegis-Force-Fail") == "true":
                self.respond_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "forced_failure"})
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self.respond_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "invalid_json", "details": str(exc)},
                )
                return

            missing = [
                field
                for field in ("payload_id", "scan_id", "device_id", "device_report", "app_snapshot")
                if field not in payload
            ]
            if missing:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"error": "missing_fields", "fields": missing})
                return

            headers = {key.lower(): value for key, value in self.headers.items()}
            store.append(payload, headers)
            self.respond_json(
                HTTPStatus.ACCEPTED,
                {
                    "accepted": True,
                    "payload_id": payload.get("payload_id"),
                    "stored_at": str(store.telemetry_path),
                },
            )

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"{self.address_string()} - {fmt % args}")

        def respond_json(self, status: HTTPStatus, body: dict[str, Any]) -> None:
            encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return AegisPocHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run tiny AEGIS telemetry POC server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for emulator/device access.")
    parser.add_argument("--port", type=int, default=8080, help="Bind port.")
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("AEGIS_POC_OUTPUT_DIR", "poc-server-data"),
        help="Directory for telemetry.jsonl and failure toggle state.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    store = TelemetryStore(output_dir)
    fail_file = output_dir / "force_fail"

    server = ThreadingHTTPServer((args.host, args.port), make_handler(store, fail_file))
    print(f"AEGIS POC server listening on http://{args.host}:{args.port}")
    print(f"Telemetry JSONL: {store.telemetry_path}")
    print("Health: GET /health")
    print("Telemetry: POST /api/v1/telemetry")
    print("Force failure: GET /fail?enabled=true or /fail?enabled=false")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AEGIS POC server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
