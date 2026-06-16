# AEGIS — Project Completion Plan (Graduation Core + Production Hardening)

**Target:** A polished, reliably demoable project (graduation core) **and** a production-grade system: real event pipeline, Play Integrity attestation, distributed rate limiting, Postgres, and deployment/CI-CD.
**Timeframe:** ~1–2 weeks for the **graduation core** (Phases 0–5) + ~3–4 weeks for the **production-hardening track** (Phases 6–11). ~5–6 weeks total.
**Basis:** 10-layer QA audit (`QA_AUDIT_REPORT_2026-06-15.md`) and the live emulator end-to-end run on 2026-06-15.

---

## Guiding principle
Get the core capabilities (scan → logs → AI risk analysis) running reliably and demoable first, then harden into a real distributed system. Each production phase ships with its own tests; comprehensive docs/CI land at the end.

---

# TRACK A — Graduation core (≈ weeks 1–2)

## Phase 0 — Make it reliably runnable (Day 1) — TOP PRIORITY
Biggest risk is the launch failing live (it did, in testing): the startup script hides uvicorn and swallows errors, default `python` is 3.14 without backend deps, and stale/duplicate listeners on 8080 silently steal traffic.

- [ ] **Rewrite `tools/start_local_mvp.ps1`**: kill **all** 8080/5173 listeners first; install deps into a **venv** (`backend/.venv`); run uvicorn **visibly/logged**; single instance on `0.0.0.0:8080`; gate on `/health` 200; start + confirm the Vite dashboard.
- [ ] **Pin the toolchain:** require Python 3.11–3.12; add `backend/requirements.txt` (or lock) and commit `frontend/package-lock.json`.
- [ ] **Smoke test:** fresh reboot → one command → backend + dashboard up → emulator reaches `10.0.2.2:8080`.

## Phase 1 — Fix the must-fix bugs (Days 2–3)
- [ ] **Null-deref guards (mypy):** `app/ai/analyzer.py:373-376`, `app/api/devices.py:73`, `app/shieldy/agent.py:58`.
- [ ] **`anas/` interim fix:** fix the fail-open hardcoded `bearer_token` (default empty + reject, constant-time compare). *Full Postgres consolidation happens in Phase 6 — don't delete it yet.*
- [ ] **Clean lint:** `ruff check --fix backend/`; fix the silent `except Exception: pass` in `app/services/ingestion.py:61`.
- [ ] **Emulator scan reliability:** add a Play-Integrity timeout/fallback so a scan always completes (full attestation comes in Phase 8).

## Phase 2 — Polish the demo path (Day 4)
- [ ] Dashboard renders the device reliably (`/devices`, `/latest-risk`, `/timeline`, `/logs/analysis`).
- [ ] Rehearse the happy path: enroll → scan → upload (`202`) → risk brief → feedback.
- [ ] Empty/loading/error states in the dashboard.

## Phase 3 — Security baseline (Day 5)
- [ ] Remove hardcoded token; fail-closed auth with `secrets.compare_digest`.
- [ ] Basic rate limiting on auth endpoints (scalable version in Phase 9).
- [ ] TLS-enabled `nginx.conf` (443 + redirect).
- [ ] `npm audit fix` the esbuild/vite HIGH advisories.

## Phase 4 — Logs pipeline: test, pull, refine the logic (Days 6–7)
Components: Android `LogFilterAgent.kt`, `LogcatReader.kt`, `ImportanceFilter.kt` → backend `/api/v1/logs/analysis`, `services/redaction.py`, clustering/summary.

- [ ] Verify log collection on the emulator (note `READ_LOGS` is privileged — establish what's accessible on AVD vs real device) and that important logs flow into the payload.
- [ ] Test the filtering logic (threat-regex, level filters, importance ranking); add/adjust unit tests.
- [ ] Confirm redaction works on real captured logs (tokens, emails, secrets, SSN/card) before storage.
- [ ] Refine the logic on real data so `/logs/analysis` returns meaningful clusters + recent logs; make the dashboard logs view demo-worthy.
- [ ] Pull/inspect stored logs end-to-end and confirm device↔backend consistency.

## Phase 5 — AI analysis: make it real and ensure it works (Days 8–10)
Today AI runs on the **stub** provider; risk is rule-based. Switch to a **real LLM** (Ollama is installed; or OpenRouter).

- [ ] Wire a real provider: `AEGIS_LOCAL_LLM_PROVIDER=ollama`, pull `llama3`, point logs/telemetry/risk models at it; or set `OPENROUTER_API_KEY` for Shieldy chat/orchestrator.
- [ ] Verify real output: `/ai/runs` + `/ai/decisions/{payload_id}` produce genuine findings with evidence refs; runs record `provider != local_stub`.
- [ ] Shieldy analyst chat answers from the device's evidence bundle.
- [ ] Keep the safety gate intact: prompt-injection blocked *before* the provider call (`security_gate.py`).
- [ ] Robustness: graceful fallback on model timeout/unavailability (no hangs).
- [ ] Surface the AI brief in the dashboard (deterministic + AI final score + reasons).

---

# TRACK B — Production hardening (≈ weeks 3–6)

## Phase 6 — Postgres data layer (reconcile the `anas/` variant)
Canonical backend runs on SQLite (sync SQLAlchemy); `anas/` is async Postgres (asyncpg, `pg_insert`). Goal: Postgres for production, SQLite kept for local dev.

- [ ] Make the canonical backend run on **Postgres** via env (`AEGIS_BACKEND_DATABASE_URL`); add psycopg/async support (pyproject already lists `psycopg[binary]`).
- [ ] Ensure Alembic migrations run cleanly on a fresh Postgres DB; **enforce foreign keys** (decorative on SQLite today).
- [ ] Fold the useful pieces of `anas/` (Postgres upsert/`on_conflict_do_nothing`) into the canonical backend, then **retire `anas/` as a separate tree** (single source of truth).
- [ ] Run the full `pytest` suite against Postgres (via docker-compose Postgres) in addition to SQLite.

## Phase 7 — Event-driven pipeline at scale (Kafka)
Currently `process_inline=true`; `consumers/*` + `kafka.py` + `worker.py` are 0% tested and unused. Goal: real async pipeline.

- [ ] Stand up Kafka (already in `docker-compose.yml`); set `AEGIS_EVENT_PUBLISHER=kafka`, `process_inline=false`.
- [ ] Make the path work end-to-end: API publishes telemetry event → `storage_consumer` persists raw → `risk_consumer` scores → AI analysis — all async.
- [ ] Add retries / dead-letter handling and idempotent consumers.
- [ ] **Integration tests for the consumers** (closes the 0%-coverage gap) + a basic load/throughput test.

## Phase 8 — Real Play Integrity backend attestation
Today the app gets a token and the UI shows "Partially verified" because the backend doesn't validate it.

- [ ] Backend verifies the Play Integrity token: decrypt/validate the integrity verdict (Google Play Integrity decryption keys or the server-side verdict endpoint via a service account).
- [ ] Check device / app / account integrity verdicts; enforce nonce/replay protection.
- [ ] Wire the verified verdict into the risk scorer (valid attestation lowers risk) and promote "Partially verified" → "Verified".
- [ ] Test with valid, tampered, and replayed tokens.

## Phase 9 — Distributed rate limiting (Redis)
Replace `InMemoryRateLimiter` (process-local + leaks stale keys) with a shared limiter.

- [ ] Add Redis (docker-compose); implement a sliding-window / token-bucket limiter in Redis.
- [ ] Apply to telemetry **and** auth/enrollment endpoints across all API instances; evict stale keys (fixes the memory leak).
- [ ] Concurrency test across multiple API replicas.

## Phase 10 — Production deployment & CI/CD
- [ ] Production `docker-compose` (or k8s manifests): API + consumers + Postgres + Kafka + Redis + nginx(TLS) + dashboard, with health checks and restart policies.
- [ ] Secrets/env management (no secrets in images or git).
- [ ] **CI/CD (GitHub Actions):** on PR run ruff + mypy + `pytest` + frontend `tsc`/build; on merge build/push images. Add status badges.
- [ ] Basic observability: structured logs + a metrics/health surface.

## Phase 11 — Comprehensive tests + documentation (final)
- [ ] Raise backend coverage (consumers, AI, Postgres paths now covered); keep everything green in CI.
- [ ] Rewrite the README run guide to the working Phase-0 flow; add a production deploy guide.
- [ ] Refresh architecture/data-flow diagrams in `docs/` to include logs, AI, Kafka, Postgres, Redis, and Play Integrity attestation.
- [ ] Demo runbook + a "Verification & Testing" chapter folding in the QA audit, live-run evidence, and logs/AI results.

---

## Definition of done
1. `start` script brings the stack up cleanly on a fresh boot, first try.
2. Live emulator → backend → dashboard demo runs end-to-end without a crash.
3. **Logs** collected, filtered, redacted, and surfaced in `/logs/analysis` + dashboard.
4. **AI** runs on a real LLM and produces genuine findings; safety gate intact.
5. **Postgres** in production with enforced FKs and clean migrations; one canonical backend.
6. **Kafka** async pipeline works end-to-end with consumer tests (no 0%-coverage modules).
7. **Play Integrity** token verified server-side; "Verified" status is real.
8. **Redis** rate limiting shared across instances; no in-memory leak.
9. **Deployment + CI/CD** green: lint + mypy + tests + build gate every PR; one-command prod bring-up.
10. Docs, run guide, and demo runbook accurate and reproducible.

## Suggested timeline
| Week | Phases | Focus |
|------|--------|-------|
| 1 | 0–3 | Reliable startup, must-fix bugs, demo polish, security baseline |
| 2 | 4–5 | Logs pipeline + real AI |
| 3 | 6–7 | Postgres data layer + Kafka pipeline at scale |
| 4 | 8 | Play Integrity backend attestation |
| 5 | 9–10 | Redis rate limiting + deployment & CI/CD |
| 6 | 11 | Comprehensive tests + documentation |
