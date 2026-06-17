# AEGIS Project — Full QA / Test Architecture Report

**Scope:** `aegis-agent/` (Android agent + sample app) and `backend/` (FastAPI telemetry/risk backend), with secondary copies under `anas/` and `.claude/worktrees/` noted where relevant.
**Constraint honored:** No code was modified, built, or deployed. This is a read-only audit.
**Note on tooling:** The sandboxed shell used for running linters, `pytest`, `pip-audit`, and Gradle was unavailable for this session (VM failed to start), so Layers 2, 4, 5, 9 and parts of 1 are based on **static/manual code review only**, not executed tool output. Findings below are flagged accordingly.

---

## Test Summary Table

| Layer | Status | Tests Run | Passed | Failed | Critical Issues |
|---|---|---|---|---|---|
| 1. Static Analysis | ⚠️ Manual only | 0 (no linter run) | – | – | Placeholder cert pins; dev `.env` with real-looking secrets on disk |
| 2. Dependency Audit | ⚠️ Manual only | 0 (no audit run) | – | – | Backend deps largely unpinned; no audit tooling configured |
| 3. Environment & Config | ✅ Pass w/ notes | – | – | – | No `prod` config profile; `.env.example` present and reasonable |
| 4. Unit Tests | ⚠️ Not executed | ~12 test files found | – | – | Could not run JUnit5/pytest; coverage unknown |
| 5. Integration Tests | ✅ Pass (traced) | Traced manually | – | – | Enrollment → ingest → score → query chain is coherent |
| 6. API Testing | ⚠️ Pass w/ issue | 8 endpoints reviewed | 7 | 1 | `/admin` console publicly reachable without auth |
| 7. Database & Data Integrity | ✅ Pass w/ notes | – | – | – | ORM-only queries (no raw SQL); Room migrations sequential |
| 8. Security Checklist | ⚠️ 6/10 ✅ | 10 items | 6 ✅ / 3 ⚠️ / 1 ❌ | – | HTTPS/cert pinning not enforced |
| 9. Performance Spot Check | ⚠️ Manual only | – | – | – | N+1 query in `/api/v1/devices` |
| 10. Frontend Testing | ⚠️ Partial | – | – | – | No standalone `frontend/` found in main tree; Android UI not exercised |

---

## Layer 1 — Static Analysis

**No dedicated linter/formatter config** (no `.flake8`, `ruff.toml`, `ktlint`/`detekt` config) was found for either the backend or the Android module, so "run the linter" could not be performed as a tool — only manual code-style review.

Findings:
- **Hardcoded-secret-shaped values:**
  - `aegis-agent/aegis-agent/.../di/NetworkModule.kt` — certificate pins are literal placeholders (`PIN_LEAF`/`PIN_BACKUP = "sha256/REPLACE_WITH_REAL_..."`). Code correctly detects and skips them, but this means pinning is **inert** in every build today.
  - `anas/backend/.env` — a real `.env` file on disk containing `DATABASE_URL` with password `aegis_pass` and `BEARER_TOKEN=aegis_dev_token_2026`. Root `.gitignore` excludes `.env`, so it *should* not be tracked, but its presence on disk in a shared workspace is itself a leak vector if this folder is ever zipped/copied.
  - `aegis-agent/local.properties` — contains a real GCP `AEGIS_CLOUD_PROJECT_NUMBER` and an emulator backend URL. Correctly gitignored.
- **`.gitignore` review:** root `.gitignore` correctly excludes `.env`/`.env.*` (with `.env.example` exception), `backend-data/`, `node_modules/`, `dist/`. `aegis-agent/.gitignore` correctly excludes `build/`, `.gradle/`, `local.properties`, `.idea/`.
- **Duplicate trees:** `anas/` and `.claude/worktrees/epic-gagarin-019b96/` contain near-complete duplicates of `aegis-agent/` and `backend/` — likely stale branches/worktrees. These inflate the repo and can cause confusion about which copy is canonical (and the duplicate `.env` lives in one of these).
- **Large/deeply nested files:** nothing pathological found; largest files are the generated `docs/*.html` assets, which are documentation, not code.

**Layer 1 verdict: ⚠️ Pass with action items** — no automated scan executed; two secret-shaped findings need attention (see Top 5).

---

## Layer 2 — Dependency Audit

`backend/pyproject.toml` dependencies:
```
fastapi, uvicorn, SQLAlchemy>=2.0, psycopg[binary]>=3.2, jsonschema, pydantic, alembic
dev: pytest, httpx
```
- Only `SQLAlchemy` and `psycopg` have floor version pins; everything else is unpinned — builds are not reproducible and could silently pick up a vulnerable/breaking release.
- No `pip-audit`, `safety`, or `dependabot`/`renovate` config found.
- Android (`aegis-agent/build.gradle.kts`): dependencies include Room, Hilt+WorkManager, OkHttp (+TLS/logging), Play Integrity, Security-Crypto, DataStore, Timber — versions weren't individually checked against CVE databases (no network access in this session). No Gradle lockfile (`gradle.lockfile`) was observed, so dependency versions can float between builds depending on the version catalog/BOM used.

**Layer 2 verdict: ⚠️ Could not execute `pip-audit`/`./gradlew dependencyCheckAnalyze`.** Recommend pinning backend deps and adding `pip-audit` + Gradle dependency-lock to CI.

---

## Layer 3 — Environment & Configuration

- `backend/.env.example` exists and documents all relevant variables (DB URL, raw payload dir, accepted tokens, rate limits, LLM/OpenRouter config). ✅
- `backend/app/config.py` (`load_settings()`) reads everything from env with sane defaults; `accepted_enrollment_tokens` / `analyst_tokens` default to **empty tuples** if unset — this fails *closed* (nothing authenticates) rather than open, which is the right default.
- `AegisDatabase`/Room and FastAPI/SQLAlchemy both default to local SQLite/file paths for dev — appropriate for local dev, but there is **no separate `prod`/`staging` settings profile or env-driven switch** beyond individual variable overrides. Production deploys rely entirely on operators setting every env var correctly.
- CORS origins default to `http://127.0.0.1:5173` / `http://localhost:5173` (Vite dev server) — reasonable for local dev, controlled via `AEGIS_CORS_ALLOWED_ORIGINS`.
- Android `local.properties` (gitignored) injects `AEGIS_BACKEND_URL=http://10.0.2.2:8080` (Android-emulator loopback to host) and a real `AEGIS_CLOUD_PROJECT_NUMBER` — fine for local dev, but there's no equivalent "release" `local.properties.example` documenting what a real device/production build should set.

**Layer 3 verdict: ✅ Pass with notes** — env handling is solid and fails closed; missing explicit prod/staging profile documentation.

---

## Layer 4 — Unit Tests

Test files discovered (canonical `aegis-agent/` tree):
- `data/apps/AppIntelligenceCollectorTest.kt`
- `data/scanner/DeviceScannerTest.kt`
- `data/logs/LogFilterAgentTest.kt`
- `data/network/TelemetryUploaderTest.kt`
- `di/AgentConfigHolderTest.kt`
- `domain/model/ScanRecordTest.kt`
- `domain/model/TelemetryPayloadTest.kt`
- `domain/usecase/UploadTelemetryUseCaseTest.kt`

Backend (`backend/tests/`):
- `test_enrollment_tokens.py`
- `test_worker_and_risk.py`
- `test_ingestion.py`
- `conftest.py`

This is a **reasonable spread** across data/scanner/network/persistence/domain layers on Android, and ingestion/risk/enrollment on the backend. However, **execution was not possible** in this session (sandbox VM failed to start), so pass/fail counts and coverage % cannot be reported.

**3 most likely under-tested / critical modules (based on absence of corresponding test files):**
1. `aegis-agent/.../di/NetworkModule.kt` — no `NetworkModuleTest`; this is the file with the disabled-cert-pinning logic, arguably the highest-risk file in the agent.
2. `aegis-agent/.../AegisSdk.kt` — no dedicated test for `init`/`shutdown`/`schedulePeriodicSync`; has a non-`@Volatile` mutable `isInitialised` flag (potential race) and re-entrancy logic that's only exercised indirectly.
3. `backend/app/main.py` / `backend/app/api/admin_ui.py` — no test exercises app wiring (CORS, router inclusion) or the admin console endpoints' auth posture.

**Layer 4 verdict: ⚠️ Not executed.** Recommend running `./gradlew testDebugUnitTest` and `pytest --cov` in a working environment before relying on this report's coverage assumptions.

---

## Layer 5 — Integration Tests (manually traced)

End-to-end flow traced through code (no live run):

1. **Enrollment**: Analyst calls `POST /api/v1/enrollment-tokens` (analyst-token protected) → `EnrollmentTokenService.create()` generates `aegis_enroll_<random>`, stores only its SHA-256 hash, returns the raw token once. Android device stores this in `AgentConfig.enrollmentToken` via `ConfigRepository` (EncryptedSharedPreferences).
2. **Device scan**: `TelemetrySyncWorker.doWork()` → `DeviceScanner.scan()` (root detection, Play Integrity, security patch date, bootloader state) + `AppIntelligenceCollector.collect()` (app inventory delta) + `LogFilterAgent.collectSnapshot()` (best-effort, swallows failures).
3. **CREATE**: `ScanResultRepository.markSuccess()` builds a payload + `payloadId`, sets `uploadStatus=PENDING`.
4. **Upload**: `TelemetryUploader.upload()` POSTs to `${backendUrl}/api/v1/telemetry` with Bearer enrollment token → backend validates against `telemetry_schema_v1.json`, dedupes by `payload_id` (idempotent), rate-limits per `device_id:client_ip`, then `IngestionService.ingest()` stores raw payload + DB row, optionally processes inline via `TelemetryWorker`.
5. **Risk scoring**: `RiskScoringService.score()` reads `DeviceReport`/`AppInventoryCurrent`/`ImportantLog`, computes a 0–100 score with reasons, persists `RiskAssessment` (idempotent on `payload_id`).
6. **READ**: Analyst queries `GET /api/v1/devices`, `/devices/{id}/latest-risk`, `/devices/{id}/timeline`, `/logs/analysis` — all analyst-token protected.
7. **UPDATE/soft-DELETE**: `POST /api/v1/enrollment-tokens/{id}/revoke` flips `is_active=false` (no hard delete anywhere — appropriate for an audit-trail system).
8. **Feedback loop**: `POST /api/v1/findings/{id}/feedback` lets analysts label findings (`TRUE_POSITIVE`, etc.) — feeds back into model/rule tuning per the docs.

**Edge cases verified by reading code:**
- Duplicate `payload_id` submission → returns `{"accepted": true, "duplicate": true}` rather than erroring (handles retries from `TelemetrySyncWorker`'s `Result.retry()`).
- Missing/expired/foreign-device enrollment token → `EnrollmentTokenService.authenticate()` returns `False`, falls back to static token list, else 401.
- Network failure during upload → `Result.retry()` in the Worker, `markUploadFailed` increments `retry_count`.
- Log collection failure during scan → caught and logged, scan still proceeds (`emptyList()` fallback).

**Layer 5 verdict: ✅ Pass** — the flow is internally consistent and handles the obvious retry/duplicate edge cases. No live DB/server was run to confirm.

---

## Layer 6 — API Testing

| Endpoint | Auth | Notes |
|---|---|---|
| `POST /api/v1/telemetry` | Enrollment token (Bearer) | Schema-validated (JSON Schema Draft 2020-12), rate-limited, idempotent on `payload_id` |
| `GET /api/v1/devices` | Analyst token | See N+1 note in Layer 9 |
| `GET /api/v1/devices/{id}/latest-risk` | Analyst token | 404 if no assessment |
| `GET /api/v1/devices/{id}/timeline` | Analyst token | `limit` clamped to 1–100 |
| `GET /api/v1/logs/analysis` | Analyst token | `limit` clamped to 1–200; filters sanitized via `normalize_filter` |
| `POST/GET /api/v1/enrollment-tokens`, `POST .../revoke` | Analyst token | Token value returned only once at creation; list never re-exposes raw token |
| `POST /api/v1/findings/{id}/feedback` | Analyst token | Label allow-list validated, 400 on invalid label |
| `GET /` and `GET /admin` | **None** | **Serves the full admin HTML/JS console with no authentication** |

**Findings:**
- ❌ **`/` and `/admin` are public.** The page itself doesn't embed secrets (the analyst token is entered client-side and stored in the browser's `localStorage`), and every actual API call is still gated by `verify_analyst_token`. However, anyone who can reach the backend can load the token-management UI and attempt to use it with a guessed/leaked analyst token, and the page reveals the existence/shape of the enrollment-token management API. This should at minimum sit behind the same network boundary as the analyst tokens, or require its own auth.
- ✅ Error codes are consistent: `202` accepted, `400` invalid schema/label, `401` unauthorized (`{"error":"unauthorized","message":...}`), `404` not found, `429` rate limited.
- ✅ No raw DB/stack-trace leakage observed in any reviewed handler — `IntegrityError` and `ValidationError` are caught and translated to structured JSON.
- ✅ Input validation: telemetry payloads validated against `telemetry_schema_v1.json` before touching the DB.

**Layer 6 verdict: ⚠️ Pass with one issue** — fix the unauthenticated admin console exposure.

---

## Layer 7 — Database & Data Integrity

- **SQL injection:** All backend queries use SQLAlchemy `select()`/ORM constructs with bound parameters — no raw string-formatted SQL found anywhere in `backend/app`. ✅
- **Migrations:** Backend uses Alembic (`alembic/versions/c56a9abf809e_initial_migration.py` + enrollment-token migration referenced by `app/models/enrollment.py`). Android uses Room with 4 explicit, additive migrations (`MIGRATION_1_2` … `MIGRATION_4_5`), each adding nullable/defaulted columns — low risk of data loss on upgrade. `exportSchema=false` means no JSON schema-history snapshots are generated for Room, so automated migration-correctness testing (`MigrationTestHelper`) isn't currently wired up. ⚠️ minor.
- **Sensitive field hashing:** Enrollment tokens are stored only as SHA-256 hashes (`hash_token()`); raw token shown once at creation. Telemetry log messages are redacted (`RedactionService` strips bearer tokens, emails, phone numbers, SSNs, credit-card-shaped strings, `key=`/`secret=`/`password=` patterns) before storage as `message_redacted`, plus a separate `message_hash` for clustering. ✅ Good defense-in-depth.
- **FKs/indexes/constraints:** `backend/app/models/*.py` were not fully read line-by-line in this pass; `RiskAssessment` is keyed by `payload_id` (unique-lookup via `.one_or_none()`), `ImportantLog` and `AppInventoryCurrent` are filtered by `device_id`/`payload_id`. Recommend a follow-up pass specifically confirming indexes exist on `device_id`, `payload_id`, and `token_hash` columns (the latter is queried on every telemetry submission, so a missing index there would be a real perf risk as the table grows).
- **N+1 / query efficiency:** see Layer 9.

**Layer 7 verdict: ✅ Pass with one follow-up** — confirm indexes on high-traffic lookup columns (`token_hash`, `payload_id`, `device_id`).

---

## Layer 8 — Security Checklist

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Password hashing | ✅ N/A→handled | No user passwords exist; enrollment tokens are high-entropy random values stored as SHA-256 hashes (acceptable for random tokens, unlike user passwords) |
| 2 | Token validation (expiry, audience) | ✅ | `EnrollmentTokenService.authenticate()` checks `is_active`, `expires_at`, optional `device_id` binding; analyst tokens checked against env allow-list |
| 3 | Input sanitization | ✅ | JSON-Schema validation on telemetry; admin UI HTML-escapes all rendered fields (`escapeHtml`) |
| 4 | CORS configuration | ⚠️ | Default origins are localhost-only (good), but `allow_credentials=True` combined with `allow_methods=["*"], allow_headers=["*"]` is a footgun if `AEGIS_CORS_ALLOWED_ORIGINS` is ever widened in prod — tighten methods/headers explicitly for production |
| 5 | Rate limiting | ⚠️ | Present on `POST /api/v1/telemetry` (`InMemoryRateLimiter`, per `device_id:client_ip`, 120/min default); **not present** on analyst-token-protected endpoints (e.g., enrollment-token creation) — lower priority since those require a valid token, but still worth limiting |
| 6 | File upload validation | ✅ N/A | No file-upload endpoints exist in the reviewed API surface |
| 7 | Error message leakage | ✅ | Structured `{"error":..., "message":...}` responses; no stack traces or raw SQL errors observed |
| 8 | Dependency CVEs | ⚠️ | Could not run `pip-audit`/Gradle CVE check this session; backend deps are largely unpinned |
| 9 | Secrets in git/on disk | ⚠️ | `anas/backend/.env` contains real-looking dev DB password and bearer token on disk (gitignore *should* exclude it, but verify it was never committed and rotate the values regardless since they're now "known") |
| 10 | HTTPS / transport security enforced | ❌ | FastAPI app itself does no TLS/HSTS enforcement (expected to be a reverse-proxy concern, but undocumented); Android `NetworkModule` certificate pinning is **disabled** because pins are placeholders — combined, there's currently no enforced transport trust anchor between agent and backend beyond standard system CA trust |

**Score: 6 ✅ / 3 ⚠️ / 1 ❌**

---

## Layer 9 — Performance Spot Check

**3 slowest/most concerning operations (by code inspection):**
1. `GET /api/v1/devices` (`backend/app/api/devices.py`) — for each distinct `device_id`, issues **two additional queries** (count + latest risk assessment). This is a classic N+1 pattern; at scale (hundreds of devices) this becomes hundreds of round-trips per dashboard load. Should be rewritten as 1–2 aggregate queries (`GROUP BY device_id` + a window/`DISTINCT ON` for latest risk).
2. `LogFilterAgent.collectSnapshot()` (Android) — launches a logcat subprocess, collects for `SNAPSHOT_WINDOW_MS=2000ms` per scan cycle. Bounded and reasonable, but every periodic sync (every ≥15 min) pays this 2-second cost plus process-spawn overhead.
3. `RootDetector` checks 7 hardcoded filesystem paths + `Superuser.apk` path synchronously on every scan — cheap individually, but it's blocking I/O (mitigated by running on `Dispatchers.IO` in `DeviceScanner`).

**Memory/growth controls (good):**
- `ScanResultRepository.pruneOldRecords(MAX_SCAN_RECORDS=25)` bounds local DB growth on-device. ✅
- `LogFilterAgent` buffer is capped (`BUFFER_MAX_SIZE=200`, TTL `10 min`) — won't grow unbounded. ✅
- `device_timeline` and `logs/analysis` both clamp `limit` (≤100 / ≤200). ✅

**Pagination:** present on the two list-heavy backend endpoints above; `GET /api/v1/enrollment-tokens` and `GET /api/v1/devices` have **no pagination** — fine while device counts are small, but will need it before a large fleet rollout.

**Layer 9 verdict: ⚠️ Pass with one real issue** — the devices-list N+1 query.

---

## Layer 10 — Frontend Testing

- The root `.gitignore` references `frontend/node_modules/` and `frontend/dist/`, implying a JS frontend was planned/exists elsewhere, but **no `frontend/` directory was found** in the main tree during this pass (only the FastAPI-served `admin_ui.py` HTML console exists today).
- **Admin console (`backend/app/api/admin_ui.py`)** — reviewed as the closest thing to a "frontend":
  - Form validation: client-side trims/defaults inputs before posting; server re-validates label/allowed-feedback values.
  - Loading/error/empty states: `setStatus()` helper shows "Loading…", success (green), and error (red) states; empty token list shows a `"No enrollment tokens yet."` row. ✅
  - All dynamic content passed through `escapeHtml()` before insertion into the DOM — no obvious DOM-based XSS. ✅
  - Stores the analyst token in `localStorage` — convenient, but means any future XSS on this origin would be able to exfiltrate the analyst token. Given the page is also unauthenticated (Layer 6 finding), this compounds that issue.
- **Android sample app UI** (`MainActivity`, `SettingsActivity`, `ScanDetailActivity`, `RiskBrief.kt`) — files exist but were not exercised for compile errors, navigation, or console errors in this pass (would require a working Gradle/emulator environment).

**Layer 10 verdict: ⚠️ Partial** — admin console reviewed and looks solid; Android sample-app UI and any separate JS frontend remain unverified.

---

## Overall Health Score

| Dimension | Score /10 | Rationale |
|---|---|---|
| Correctness | 7/10 | Core flows (enrollment → scan → upload → risk score → query) are logically sound and handle retries/duplicates; couldn't confirm via running tests |
| Security | 6/10 | Good redaction, hashing, schema validation, fail-closed auth defaults — offset by disabled cert pinning, public admin console, no enforced HTTPS |
| Test Coverage | 6/10 | Solid spread of unit tests across both codebases by file count; actual coverage % unknown, UI layers untested |
| Code Quality | 7/10 | Clean architecture, good KDoc/comments, consistent error handling; some duplication (anas/, worktrees) and unpinned deps |
| Production Readiness | 5/10 | Multiple "dev mode" defaults (placeholder cert pins, localhost CORS, SQLite, unpinned deps, no prod profile) would all need addressing before a real rollout |

---

## Top 5 Issues to Fix Immediately

1. **Certificate pinning is inert (placeholder pins).**
   File: `aegis-agent/aegis-agent/src/main/java/com/aegis/agent/di/NetworkModule.kt`
   Fix: Generate real `sha256/...` pins for `api.aegis.internal` (leaf + backup CA) and replace `PIN_LEAF`/`PIN_BACKUP`. Add a CI check that fails the build if `REPLACE_WITH_REAL` is still present in a release config.

2. **Unauthenticated admin console exposes the enrollment-token management UI.**
   File: `backend/app/api/admin_ui.py` (routes `/` and `/admin`)
   Fix: Gate `/admin` behind `verify_analyst_token` (e.g., require the token as a query param on first load, or move it behind the same reverse-proxy ACL as the rest of the analyst API), and avoid storing the analyst token in `localStorage`.

3. **N+1 query pattern in `GET /api/v1/devices`.**
   File: `backend/app/api/devices.py`
   Fix: Replace the per-device `count` + `latest risk` queries with a single aggregated query (e.g., `GROUP BY device_id` for counts, and a correlated subquery / `DISTINCT ON (device_id) ORDER BY created_at DESC` for latest risk).

4. **Real-looking dev secrets present on disk in `anas/backend/.env`** (DB password `aegis_pass`, `BEARER_TOKEN=aegis_dev_token_2026`).
   File: `anas/backend/.env`
   Fix: Confirm this file was never committed (`git log --all -- anas/backend/.env`), delete it from the working tree, and rotate any credential that matches a real environment even though these look like placeholders.

5. **Backend dependencies are unpinned and no audit tooling is configured.**
   File: `backend/pyproject.toml`
   Fix: Pin all dependencies to known-good versions (or use a lockfile via `pip-compile`/`uv`), and add `pip-audit` (backend) and a Gradle dependency-vulnerability check (Android) to CI.

---

## What Is Safe to Ship Right Now

**Nothing should go to production in its current state** — but the project is closer to "internal pilot ready" than "broken":

- The **Android agent's core data pipeline** (root detection, app-inventory delta collection, log filtering, Room persistence with safe migrations, WorkManager scheduling, encrypted local config storage) is well-architected, defensively coded (lots of `runCatching`/graceful degradation), and appears safe to run on **test/lab devices against a non-public backend**.
- The **backend's ingestion → risk-scoring → query pipeline** is internally consistent, uses parameterized queries throughout, redacts sensitive log content before storage, and has reasonable input validation and rate limiting on the highest-volume endpoint.
- **Before any pilot beyond a closed lab network:** configure real certificate pins, lock down `/admin`, and fix the CORS/transport-security gaps in Layer 8.
- **Before any multi-device or production rollout:** fix the N+1 devices query, add pagination to `/api/v1/devices` and `/api/v1/enrollment-tokens`, pin and audit dependencies, and re-run this audit's Layers 2/4/5/9 with a working test runner to get real pass/fail/coverage numbers.
