# AEGIS Mobile Security Scanner

[![CI](https://github.com/samir22418/mobile_sec/actions/workflows/ci.yml/badge.svg)](https://github.com/samir22418/mobile_sec/actions/workflows/ci.yml)

AEGIS is an Android mobile security scanner and lightweight EDR proof of concept.
It collects local device posture, app inventory, selected security logs, and upload
state so a backend/data engineering team can validate, enrich, and process the
telemetry later.

The current focus is the Android agent, sample scanner UI, and a local backend
MVP for ingestion, normalization, risk scoring, logs analysis, local AI audit
flows, the Shieldy/OpenRouter analyst chatbot adapter, and a React/Vite analyst
console. The legacy POC server remains available for simple upload smoke tests.

## What Is Included

- Android security agent library in `aegis-agent/aegis-agent`
- Sample Android scanner app in `aegis-agent/app`
- Local Room persistence for scan records
- WorkManager upload queue and retry flow
- Play Integrity token collection state
- Root, bootloader, patch, app inventory, and important log signals
- Local risk brief and analyst-friendly scan detail UI
- Dark/light theme support
- Local FastAPI backend MVP in `backend`
- POC telemetry server in `aegis-agent/poc-server`
- Backend/data engineer handoff documentation in `docs`

## Important Integrity Note

If Google Play Integrity returns a token, the UI shows the device as
`Partially verified`.

That means the Android app received a Play Integrity token, but final trust still
requires backend validation. The client does not decode or fully trust the token
locally.

## Repository Layout

```text
mobile_sec/
  README.md
  aegis-agent/
    aegis-agent/      Android agent library
    app/              Sample scanner app
    poc-server/       Python POC telemetry receiver
    gradle/           Android build configuration
  backend/            FastAPI backend MVP
  backend-data/       Local runtime DB/raw payloads, ignored by git
  docs/               Project guides, phases, handoff notes
```

## Quick Start — local dev

**Requirements:** Python 3.11–3.13, Node 18+, Android Studio (Hedgehog+).

### 1. Start the full stack (one command)

```powershell
# From repo root — kills stale listeners, creates venv, runs migrations,
# starts uvicorn + Vite, and waits for /health 200 before returning.
.\tools\start_local_mvp.ps1
```

- Backend API: `http://127.0.0.1:8080`
- Analyst dashboard: `http://127.0.0.1:5173`
- Health check: `http://127.0.0.1:8080/health`

### 2. Build and run the Android agent

```powershell
cd aegis-agent
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"

# Build + unit tests
.\gradlew.bat :aegis-agent:testDebugUnitTest :app:assembleDebug

# Install on a running emulator
adb install -r .\app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.aegis.agent.sample/.ui.MainActivity
```

Make sure `aegis-agent/local.properties` points at the backend:
```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
AEGIS_CLOUD_PROJECT_NUMBER=123456789012   # for Play Integrity
```

### 3. Run backend tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -q   # 115+ tests
```

### 4. Production docker-compose

```bash
cd backend
cp .env.production.example .env   # fill in secrets
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/aegis.key \
  -out certs/aegis.crt -sha256 -days 365 -nodes -subj "/CN=localhost"
docker compose up --build -d
```

All services (API, worker, Postgres, Kafka, Redis, nginx, dashboard) start with health checks and restart policies. Dashboard available at `https://localhost`.

See [Demo Runbook](docs/demo-runbook.md) for the full verification guide.

## Configuration

For emulator uploads to the local POC server, make sure
`aegis-agent/local.properties` contains:

```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
```

For real Play Integrity testing, add your numeric Google Cloud project number:

```properties
AEGIS_CLOUD_PROJECT_NUMBER=123456789012
```

## Main User Flow

1. Run the POC server.
2. Build and install the Android sample app.
3. Open the scanner UI.
4. Tap `Run Security Scan`.
5. Review the dashboard risk score, upload state, and recommended action.
6. Open scan details for device posture, app inventory, logs, and JSON evidence.
7. Share or copy the analyst brief for backend/data engineering review.

## Documentation

| Doc | Contents |
|---|---|
| [Architecture Overview](docs/architecture-overview.md) | Full data-flow diagram, service map, DB schema, AI pipeline |
| [Demo Runbook](docs/demo-runbook.md) | Step-by-step demo path + verification commands |
| [Play Integrity Guide](docs/play-integrity-real-device-guide.md) | Real-device attestation setup |
| [Backend Handoff](docs/backend-data-engineering-handoff.md) | Data engineering integration guide |
| [AI Architecture](docs/ai-llm-threat-analysis-architecture.md) | LLM multi-model pipeline design |

## What is implemented

| Capability | Status |
|---|---|
| Android agent (root / bootloader / patch / app inventory / logs) | Done |
| Play Integrity token collection + backend `decodeIntegrityToken` | Done |
| Nonce / replay protection | Done |
| FastAPI telemetry ingestion + JSON Schema validation + redaction | Done |
| Normalisation → Postgres (SQLite for dev) via Alembic | Done |
| Deterministic risk scoring (0–100) | Done |
| Multi-model AI analysis (OpenRouter / Ollama / stub) | Done |
| Kafka async pipeline + TelemetryConsumer (retry + DLQ) | Done |
| Redis distributed rate limiting (sliding window, fallback) | Done |
| React/Vite analyst dashboard | Done |
| nginx TLS proxy | Done |
| GitHub Actions CI (lint + types + 115 tests + frontend build) | Done |
| Docker CD → GHCR on merge | Done |
| Structured JSON logging | Done |
| Rich `/health` endpoint (DB + Redis + Kafka) | Done |
| Production docker-compose (all services + healthchecks) | Done |

## Validation Command

Use this before sharing changes:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\aegis-agent
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest :app:assembleDebug
```

Expected result:

```text
BUILD SUCCESSFUL
```
