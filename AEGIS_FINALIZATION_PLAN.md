# AEGIS — Finalization Plan

Three scope changes to land, then finalize: **fix the OpenRouter chatbot**, **remove Play Integrity** (simplify), **integrate the APK analyzer** (AEGIS APK Studio), then polish for submission.

---

## Phase 1 — Fix the OpenRouter chatbot (quick win, do first)

**Root cause:** the backend reads `OPENROUTER_API_KEY` from the process environment at `create_app()` time and **does not auto-load `.env`** (no `dotenv` in `backend/app/config.py`). The chat modules (`app/shieldy/providers.py:31`, `app/ai/chat.py`) raise *"OpenRouter is not configured"* whenever `settings.openrouter_api_key` is empty in the **running** process. So adding the key to `.env` does nothing until the backend is restarted by a launcher that loads `.env`.

**Fix:**
1. Add `python-dotenv` loading to `backend/app/config.py` (load `backend/.env` before reading env vars) so *any* launch honors `.env`. Add `python-dotenv` to `requirements.txt`.
2. Verify the `.env` line format: `OPENROUTER_API_KEY=sk-or-...` — no quotes, no spaces, single line.
3. Restart the backend (`run_real2.bat`, which already loads `.env`) so the new key is picked up.
4. Verify: `POST /api/v1/chat/sessions` then a message returns a real answer (not `chat_not_configured`). Chat works regardless of `AEGIS_LOCAL_LLM_PROVIDER` — it uses the OpenRouter key directly.

*Est: ~30 min.*

---

## Phase 2 — Remove Play Integrity (simplify)

### Android app (`aegis-agent/`)
- Delete `data/scanner/IntegrityApiClient.kt` and remove its DI wiring in `di/ScannerModule.kt`.
- Remove Play Integrity collection from `data/scanner/DeviceScanner.kt`; drop integrity fields from `domain/model/DeviceReport.kt`, the telemetry payload, and `ScanRecord`.
- Update UI to stop showing integrity: `app/.../MainActivity.kt`, `RiskBrief.kt`, `ScanDetailActivity.kt`, plus `res/layout/activity_main.xml` and `activity_scan_detail.xml`.
- Trim affected tests (`DeviceScannerTest`, `TelemetryPayloadTest`, `UploadTelemetryUseCaseTest`, `TelemetryUploaderTest`).
- Remove the `playIntegrity` dependency from the gradle version catalog.

### Backend (skip cleanly)
- Make `integrity_verdict` **optional** in `app/schemas/telemetry_schema_v1.json` and `app/models/telemetry.py` (since the app will no longer send it).
- Remove the `PlayIntegrityService` verification step from `app/main.py`, `app/services/ingestion.py`, and `app/consumers/telemetry_consumer.py` (or leave the service as the existing no-op bypass — it already returns a bypass verdict when unconfigured).
- Adjust `app/risk/scorer.py` so a **missing** integrity verdict doesn't break scoring or unfairly penalize the device.
- Drop the `AEGIS_GOOGLE_PLAY_INTEGRITY_*` env vars and `app/services/play_integrity.py` (optional cleanup).
- Keep `pytest` green (update/remove the Play Integrity tests).

*Note: the backend already "skips" it today because the API key is unset — so the urgent part is the Android app + making the schema field optional.*

---

## Phase 3 — Integrate the APK analyzer (AEGIS APK Studio)

The repo is a full product (FastAPI backend :8000 + React/Vite frontend + Ollama AI + optional PostgreSQL) that analyzes **uploaded APK files**: static analysis, dynamic emulator sandbox, deterministic risk, specialist classifiers, MITRE ATT&CK, evidence-fused local AI, HTML/PDF reports, evaluation metrics. Your project covers **device telemetry**. Same stack → clean to combine.

**DECISION NEEDED — pick the integration depth:**

### Option A — Unified product, two cooperating services *(recommended for finalizing)*
- Clone APK Studio into the repo (e.g. `apk-studio/`); run its backend on **:8000**, reuse the **shared Ollama**.
- Add a top-nav link / small unified landing in your dashboard so one AEGIS console gives access to **both**: device-posture monitoring (your app) **and** APK file analysis (APK Studio).
- Optionally share one PostgreSQL instance.
- **Pros:** fastest, lowest risk, both codebases stay intact and individually testable; very strong demo narrative ("device monitoring + APK analysis under one AEGIS console"). **Cons:** two backend processes.

### Option B — Deep merge into one backend
- Port APK Studio's analysis modules (`intake`, `static_analysis`, `risk`, `specialist_classifiers`, `ai_analysis`, `report`) into your backend as an `apk/` package with `/api/v1/apk/jobs` endpoints; add APK upload + report views to your React dashboard.
- **Pros:** single unified service. **Cons:** much more work — reconciling schemas, the two AI routers, report engines, and DB layers; higher risk; harder to keep tests green.

**Steps (Option A):**
1. Clone + run APK Studio (backend :8000, its frontend), point it at your existing Ollama.
2. Verify end-to-end with a sample APK: upload → static analysis → risk → report; run dynamic analysis against the **already-running emulator** (it shares ADB).
3. Add navigation between the two dashboards (links, or a one-page launcher).
4. Optional: consolidate to one PostgreSQL and one Ollama config; align ports so one launcher starts everything.

---

## Phase 4 — Finalize

- **One launcher** brings up the whole stack: your backend :8080, dashboard :5173, APK Studio :8000, Ollama, emulator.
- `pytest` green on both backends; lint/type clean.
- **Docs:** update README + run guide to the working flow; refresh the architecture diagram to show *telemetry + APK analysis + shared AI*; write a demo runbook.
- **Repo hygiene:** remove the helper `*.bat` / `*.log` / `*_output.txt` clutter from earlier sessions; commit on a feature branch.
- Final clean-boot dry run of the combined demo.

---

## Suggested order & rough effort
| Phase | Effort | Notes |
|-------|--------|-------|
| 1 — Chatbot fix | ~30 min | Do first; unblocks the chat demo |
| 2 — Remove Play Integrity | ~0.5–1 day | App is the bulk; backend mostly schema-optional |
| 3 — APK Studio (Option A) | ~1–2 days | Clone, run, wire UI nav, verify with a sample APK |
| 3 — APK Studio (Option B) | ~1+ week | Only if you want a single merged service |
| 4 — Finalize | ~1 day | Launcher, tests, docs, demo |

**The one thing I need from you to proceed past the plan:** Option A (cooperating services) or Option B (deep merge) for the APK analyzer.
