# AEGIS Agent Phase 7 - POC Server

## What Changed

The repo now includes a tiny telemetry receiver for agent upload/retry testing.

It is intentionally not a production backend. It has no auth, no database, no Kafka, no mTLS, and no risk engine.

## Server

File:

```text
poc-server/aegis_poc_server.py
```

Run from repo root:

```powershell
python .\poc-server\aegis_poc_server.py --host 0.0.0.0 --port 8080
```

Endpoints:

```text
GET  /health
POST /api/v1/telemetry
GET  /fail?enabled=true
GET  /fail?enabled=false
```

Accepted telemetry is appended to:

```text
poc-server-data/telemetry.jsonl
```

## Retry Testing

Turn forced failures on:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=true
```

Turn forced failures off:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=false
```

When forced failure is enabled, `POST /api/v1/telemetry` returns HTTP 500 so the Android agent should keep the scan queued and retry.

## Sample App Config

The sample app now reads backend URL from `local.properties` or Gradle property:

```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
```

Use `10.0.2.2` from the Android emulator to reach a server running on the host machine.

For a physical device, use your host machine LAN IP instead.

The sample app allows cleartext traffic so HTTP POC testing works. This is only in the sample app, not the agent library.

## Smoke Test

From repo root:

```powershell
$server = Start-Process python -ArgumentList '.\poc-server\aegis_poc_server.py --host 127.0.0.1 --port 8080 --output-dir .\build\poc-server-smoke' -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
Invoke-RestMethod http://127.0.0.1:8080/health
Stop-Process -Id $server.Id
```

## Next Phase

Run emulator end-to-end:

1. Start this POC server.
2. Set `AEGIS_BACKEND_URL=http://10.0.2.2:8080`.
3. Build/install sample app.
4. Tap "Run Security Scan".
5. Verify `telemetry.jsonl` receives a payload.
6. Toggle `/fail?enabled=true` and verify retry metadata changes.
