# AEGIS Mobile Security Scanner

[![CI](https://github.com/samir22418/mobile_sec/actions/workflows/ci.yml/badge.svg)](https://github.com/samir22418/mobile_sec/actions/workflows/ci.yml)

AEGIS is an Android mobile security scanner and lightweight EDR proof of concept.
It collects local device posture, app inventory, selected security logs, and upload
state so a backend/data engineering team can validate, enrich, and process the
telemetry later.

The platform has two integrated components:

- **Device telemetry** (this repo's main service on `:8080`): Android agent collecting
  root detection, security patch date, bootloader state, app inventory, and logs →
  FastAPI ingestion → deterministic + AI risk scoring → React/Vite analyst console.
- **APK static & dynamic analysis** (APK Studio on `:8000`, in `apk-studio/`): uploads
  APK files for disassembly, emulator sandbox, MITRE ATT&CK tagging, and AI-fused
  risk reports. Accessible directly from the AEGIS console's "APK Analyzer" tab.

## What Is Included

- Android security agent library in `aegis-agent/aegis-agent`
- Sample Android scanner app in `aegis-agent/app`
- Local Room persistence for scan records
- WorkManager upload queue and retry flow
- Root detection, bootloader state, security patch date, app inventory, and important log signals
- Local risk brief and analyst-friendly scan detail UI
- Dark/light theme support
- Local FastAPI backend MVP in `backend`
- APK Studio integration scaffold in `apk-studio/` (clone the repo there to activate)
- POC telemetry server in `aegis-agent/poc-server`
- Backend/data engineer handoff documentation in `docs`

## Repository Layout

```text
mobile_sec/
  README.md
  aegis-agent/
    aegis-agent/      Android agent library
    app/              Sample scanner app
    poc-server/       Python POC telemetry receiver
    gradle/           Android build configuration
  backend/            FastAPI backend MVP (device telemetry, :8080)
  apk-studio/         APK analysis service (clone here, runs on :8000)
  frontend/           React/Vite analyst console (:5173)
  backend-data/       Local runtime DB/raw payloads, ignored by git
  docs/               Project guides, phases, handoff notes
  tools/              PowerShell dev scripts (start_local_mvp.ps1)
```

## Quick Start — local dev

**Requirements:** Python 3.11–3.13, Node 18+, Android Studio (Hedgehog+).

### 1. Start the full stack (one command)

```powershell
# From repo root — kills stale listeners, creates venv, runs migrations,
# starts uvicorn + Vite, and waits for /health 200 before returning.
.\tools\start_local_mvp.ps1

# With APK Studio (requires apk-studio/ cloned):
.\tools\start_local_mvp.ps1 -StartApkStudio
```

- Backend API: `http://127.0.0.1:8080`
- Analyst dashboard (device telemetry + APK Analyzer tab): `http://127.0.0.1:5173`
- APK Studio (when started): `http://127.0.0.1:8000`
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
```

### 3. Run backend tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app/ tests/   # lint gate
.\.venv\Scripts\python.exe -m pytest tests/ -q          # 115+ tests
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
| [Design System](docs/design-system.md) | Color tokens, risk scale, typography, chart components |
| [Play Integrity Guide](docs/play-integrity-real-device-guide.md) | Real-device attestation setup |
| [Backend Handoff](docs/backend-data-engineering-handoff.md) | Data engineering integration guide |
| [AI Architecture](docs/ai-llm-threat-analysis-architecture.md) | LLM multi-model pipeline design |

## What is implemented

| Capability | Status |
|---|---|
| Android agent (root / bootloader / patch / app inventory / logs) | Done |
| Nonce / replay protection | Done |
| FastAPI telemetry ingestion + JSON Schema validation + redaction | Done |
| Normalisation → Postgres (SQLite for dev) via Alembic | Done |
| Deterministic risk scoring (0–100) | Done |
| Multi-model AI analysis (OpenRouter / Ollama / stub) | Done |
| Kafka async pipeline + TelemetryConsumer (retry + DLQ) | Done |
| Redis distributed rate limiting (sliding window, fallback) | Done |
| React/Vite analyst dashboard with APK Analyzer tab | Done |
| APK Studio integration scaffold (`apk-studio/`, launcher flag) | Done |
| Unified dark design system — shared tokens, risk scale, Recharts charts | Done |
| nginx TLS proxy | Done |
| GitHub Actions CI (lint + types + 115 tests + frontend build) | Done |
| Docker CD → GHCR on merge | Done |
| Structured JSON logging | Done |
| Rich `/health` endpoint (DB + Redis + Kafka) | Done |
| Production docker-compose (all services + healthchecks) | Done |

## Visual Identity

All three surfaces share one dark "cyber security" design system. See [docs/design-system.md](docs/design-system.md) for the full token reference.

- **Background layers:** `#080D13` (base) → `#111922` (surface) → `#182535` (elevated)
- **Accents:** cyan `#64D2FF` (primary / interactive) + violet `#A78BFA` (AI / MITRE)
- **Risk scale (identical everywhere):** Low `#46D39A` · Medium `#F4B740` · High `#F97316` · Critical `#FF6B6B` · Unknown `#95A3B3`
- **Charts:** Recharts in both React apps — fleet risk donut, score timeline, log level bars, classifier scores, MITRE technique frequency
- **Favicon:** shared SVG shield (`frontend/public/aegis-icon.svg`) wired into both web apps

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
