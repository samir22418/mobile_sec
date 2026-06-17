# AEGIS — Full QA & Test Architecture Audit

**Project:** AEGIS Mobile Security Scanner (Android agent + FastAPI backend + React/Vite analyst console + POC server)
**Audited by:** Senior QA / Test Architect pass
**Date:** 2026-06-15
**Scope:** `backend/` (canonical), `frontend/`, `aegis-agent/` (static review only — no Android SDK in test env), and the `anas/` teammate copy.
**Mandate:** Test, report, and suggest fixes only. **Nothing was shipped, deployed, or modified.**

> Note on environment artifacts: several "failures" encountered during testing were caused by the sandbox's read-only mount of the project folder (SQLite *disk I/O error*, `EPERM unlink` on `dist/`, coverage file write). These are flagged inline and are **not** code defects.

---

## Test Summary Table

| Layer | Status | Tests Run | Passed | Failed | Critical Issues |
|-------|--------|-----------|--------|--------|-----------------|
| 1. Static Analysis | ⚠️ Pass w/ warnings | ruff + mypy + tsc + secret scan | tsc clean; ruff backend 13 / anas 23; mypy 5 | — | Hardcoded default bearer token in `anas` source; 5 mypy null-deref risks |
| 2. Dependencies | ⚠️ Pass w/ warnings | pip-audit ×2 + npm audit | Python clean | 2 HIGH (frontend) | No lock files committed anywhere; stale Android deps |
| 3. Configuration | ⚠️ Pass w/ warnings | manual + code trace | — | — | `anas` fails *open* to a known token; no env-validation on startup |
| 4. Unit Tests | ✅ Pass (canonical) / ⚠️ anas | 45 | 42 | 3 (anas) | Kafka pipeline 0% coverage; anas test harness can't create schema |
| 5. Integration | ✅ Pass | full e2e suite | all | 0 | — |
| 6. API | ✅ Pass | 18 routes probed | 15/15 auth-gated | 0 | `/admin` console served publicly; import-time DB DDL |
| 7. Database | ⚠️ Pass w/ warnings | schema + migration review | — | — | SQLite FKs not enforced; dual schema-management paths |
| 8. Security | ⚠️ Partial | 10-point checklist | 6 Pass | 1 Fail / 3 Partial | HTTPS not enforced; rate-limit gaps; hardcoded token |
| 9. Performance | ⚠️ Pass w/ warnings | code trace | — | — | N+1 on `/devices`; unbounded lists; rate-limiter memory leak |
| 10. Frontend | ✅ Pass | tsc + vite build | clean | 0 | Thin empty-state handling; default token in client |

---

## Layer-by-Layer Findings

### Layer 1 — Static Analysis ⚠️
- **Linting (ruff):** 13 issues in `backend/`, 23 in `anas/backend/` — all low severity (unused imports, imports-not-at-top, unused vars, ambiguous names). No correctness-breaking errors.
- **Type checking:** Frontend `tsc --noEmit` **clean**. Backend `mypy` reports **5 errors in 3 files**, two of which are genuine null-dereference risks:
  - `backend/app/ai/analyzer.py:373-376` — `LLMAnalyzer | None` used without a `None` guard (`.model_name`, `.analyze`, …).
  - `backend/app/api/devices.py:73` — may return `None` where a `dict` is declared.
  - `backend/app/shieldy/agent.py:58` — incompatible type passed to `ShieldyTurnResponse`.
- **Secrets:** Canonical `backend/app/config.py` is clean and fully env-driven (empty token defaults, localhost-only CORS). ❌ **`anas/backend/app/config.py:10` hardcodes `bearer_token = "aegis_dev_token_2026"`** as a committed default, and `anas/backend/.env` carries the same token + DB creds (the `.env` is gitignored/untracked, which is correct).
- **`.gitignore`:** Present and solid — `.env`, `.env.*` (with `!.env.example`), `backend-data/`, `node_modules/`, `dist/`. `git ls-files` confirms **no** `.env`/secret/`.db` files are tracked.
- **Large files (>500 lines):** `analyzer.py` (820), `frontend/src/App.tsx` (617), `dashboard/app.py` (575), `MainActivity.kt` (497). Silent exception swallow at `backend/app/services/ingestion.py:61` and `anas/.../telemetry.py:75`.

### Layer 2 — Dependency Audit ⚠️
- **Python:** `pip-audit` reports **no known vulnerabilities** for either backend.
- **Frontend:** `npm audit` → **2 HIGH** (`esbuild` ≤0.28.0 via `vite`: RCE via `NPM_CONFIG_REGISTRY` + arbitrary file read). Impact is limited to the local dev server; fix requires `vite@8` (breaking).
- **❌ Lock files:** none committed. `frontend/package-lock.json` exists locally but is **untracked**; `backend/pyproject.toml` pins nothing; `anas/requirements.txt` uses open `>=` ranges. Builds are non-reproducible.
- **Stale deps:** Android libs pinned to late-2023/early-2024 (Kotlin 1.9.22, coroutines 1.7.3, Room 2.6.1, AGP 8.13.2, compileSdk 34) — all >1 year old.

### Layer 3 — Environment & Configuration ⚠️
- `.env.example` present and thorough for both backends (canonical documents ~25 vars; `anas` uses `change_me_in_production`). Minor: `AEGIS_CORS_ALLOWED_ORIGINS` is read by code but absent from the example.
- **Graceful failure:** Canonical backend is **fail-closed** — unset token env → empty accepted set → every token rejected (401). Safe, but *silent* (no startup warning that auth is unconfigured). **`anas` is fail-open** — `verify_bearer` defaults to the hardcoded `aegis_dev_token_2026`, so a missing env var silently accepts a publicly-known credential. The comparison is also non-constant-time (`!=`).
- **Config separation:** Good — both env-driven; canonical injects test settings via `conftest.py`, ships `docker-compose.yml`, keeps DB/ports/CORS out of source. Neither does explicit startup env validation.

### Layer 4 — Unit Tests ✅ / ⚠️
- **Canonical backend: 35 passed, 0 failed, 0 skipped. Coverage 81%** (1841 stmts, 351 missed).
- **0% coverage — the entire Kafka event pipeline:** `consumers/risk_consumer.py` (46), `consumers/storage_consumer.py` (35), `consumers/entrypoint.py` (32), `worker.py` (27), `kafka.py` (8).
- **3 most critical untested modules:** `risk_consumer.py` (risk scoring in event mode), `storage_consumer.py` (payload persistence), `kafka.py`/`worker.py` (bus + entrypoint). Also thin: `shieldy/providers.py` (58%, live LLM calls).
- **anas backend: 7 passed, 3 failed.** All 3 failures = `no such table: telemetry_payloads` — `conftest.py` provides only data fixtures and **never creates the schema** (no `create_all`/`init_db` fixture). The DB-touching tests cannot run standalone.

### Layer 5 — Integration Tests ✅
The canonical `test_e2e_flow.py` exercises the full lifecycle against in-process FastAPI + throwaway SQLite: mint enrollment token → submit telemetry → validate/store/score inline → read `/devices`, `/latest-risk`, `/timeline`, `/logs/analysis` → feedback → revoke token (and reject reuse) → idempotent duplicate replay. All flows pass. Edge cases covered: empty logs, stale-inventory replacement, invalid label, bad auth, duplicate, rate limit. Third-party AI flow blocks prompt injection *before* calling the provider and returns a clean config error when the API key is absent.

### Layer 6 — API Testing ✅
18 routes enumerated; **all 15 data endpoints return 401 without credentials**; only `/`, `/health`, `/admin` are open. Validation verified: missing field → 400 `invalid_schema`; wrong type → 422; unknown id → 404; bad enum → 400 with allowed list; negative limit → clamped. **No stack traces / DB errors leak** (generic 500, no `debug=True`, no custom handler). CORS env-driven, localhost default. Notes: `/admin` serves the analyst console HTML publicly (data calls still require a token); `app/main.py` runs `create_app()` at module import (DB DDL on import → fragile).

### Layer 7 — Database & Data Integrity ⚠️
- **Schema:** strong — FKs on `payload_id`, comprehensive indexes, unique constraints incl. composite `uq_device_package`.
- **Migrations:** clean 2-revision Alembic chain.
- **SQL injection:** none — ORM throughout; single hardcoded `text()` ALTER with no user input.
- **Sensitive fields:** enrollment tokens via `secrets`, stored as SHA-256 hashes; no plaintext creds.
- ⚠️ **SQLite FKs not enforced** (no `PRAGMA foreign_keys=ON`) → orphan rows possible on default DB.
- ⚠️ **Dual schema management** — Alembic *and* `create_all` *and* a runtime `ALTER TABLE` shim (`ensure_runtime_schema`), which is itself evidence of drift.
- `anas` is Postgres-only (`pg_insert`) despite a SQLite config default → cannot run on its own default DB.

### Layer 8 — Security Checklist
1. Passwords hashed — ✅ N/A (token auth; tokens hashed, no plaintext).
2. Tokens validated on every protected route — ✅ canonical / ❌ anas (hardcoded default).
3. Input sanitized — ✅ ORM-parameterized, no shell/eval, PII+secret log redaction.
4. CORS not wildcard in prod — ✅ env-driven, localhost default.
5. Rate limiting on auth endpoints — ⚠️ Partial (only `/telemetry`).
6. File-upload validation — ✅ N/A (no upload endpoints).
7. Errors don't leak stack traces — ✅ verified.
8. No critical CVEs — ⚠️ 2 HIGH (esbuild/vite, dev-only); Python clean.
9. Secrets not in git — ⚠️ none tracked, but anas hardcodes a default token in committed source.
10. **HTTPS enforced in prod — ❌ `nginx.conf` listens on port 80 only; no TLS/redirect.**

### Layer 9 — Performance Spot Check ⚠️
- **Top 3 expensive ops:** (1) `GET /devices` — N+1 (1 + 2×N queries) + unbounded result; (2) `GET /devices/{id}/timeline` — per-record risk lookup (N+1, clamped to 100); (3) `analyzer.py` — synchronous LLM calls (≤90s) in request path + one JSON file written to disk per payload.
- **Indexes:** comprehensive — existing queries are index-backed.
- **Pagination:** missing on `/devices` and `/enrollment-tokens` (unbounded); present/clamped on `/logs/analysis`, `/timeline`, `/ai/runs`.
- **Memory leak:** `InMemoryRateLimiter._buckets` never evicts stale `device:host` keys → unbounded dict growth. Also unbounded raw-payload files in `backend-data/raw-payloads` (no rotation/cleanup).

### Layer 10 — Frontend Testing ✅
`tsc --noEmit` clean; `vite build` succeeds (1580 modules, 214 KB JS / 67 KB gzipped). No broken imports/undefined vars. API URL env-driven; path params `encodeURIComponent`-escaped; `request()` throws on non-OK. Tab-based SPA → no unresolvable routes. No stray `console.log`. Error states strong; **empty-state handling thin**. `api.ts` ships a hardcoded default token `"sample-token"`. Live runtime console-error capture was not possible without a running backend + browser; the build emits zero warnings.

---

## Overall Health Score

- **Correctness** (does it do what it's supposed to?): **8/10** — canonical backend logic is well-tested and behaves correctly end-to-end; minor null-deref risks and the untested event-pipeline path hold it back.
- **Security**: **5/10** — solid fundamentals on the canonical backend (fail-closed auth, hashed tokens, no injection, no leakage), dragged down by no HTTPS, a hardcoded fail-open token in `anas`, and rate-limiting gaps.
- **Test Coverage**: **7/10** — 81% on the canonical backend with a real e2e suite; zero coverage on Kafka consumers and a broken `anas` harness.
- **Code Quality**: **7/10** — clean typing on the frontend, consistent ORM usage, good redaction; weakened by dual schema paths, import-time side effects, large files, and lint debt.
- **Production Readiness**: **4/10** — this is an MVP/graduation prototype: no lock files, no TLS, in-memory rate limiter that leaks, Kafka path untested, `anas` duplicate with insecure defaults.

---

## Top 5 Issues to Fix Immediately

1. **HTTPS not enforced (`backend/nginx.conf`).** Listens on port 80 only. → Add a TLS server block (443) with certs and a 80→443 redirect before any non-local deployment.
2. **Hardcoded fail-open auth token in `anas/backend/app/config.py:10`** (`bearer_token = "aegis_dev_token_2026"`). → Change the default to empty/`None` and **reject requests when unset** (fail-closed, matching the canonical backend). Use a constant-time compare (`secrets.compare_digest`).
3. **No dependency lock files committed (all components).** → Commit `frontend/package-lock.json`, pin `backend/pyproject.toml` versions (add a lock via `uv`/`pip-tools`), and pin `anas/requirements.txt`. Then run `npm audit fix` for the esbuild/vite HIGH advisories.
4. **Null-dereference risks flagged by mypy** — `backend/app/ai/analyzer.py:373-376` (and `api/devices.py:73`). → Add explicit `None` guards before using `LLMAnalyzer`; make `analyzer.py` resilient when the analyzer is unconfigured (it's hit on AI endpoints).
5. **N+1 + unbounded results on `GET /api/v1/devices` (`backend/app/api/devices.py`).** → Replace the per-device loop with a single grouped/joined query (e.g., a window function for latest risk + aggregate count) and add pagination (`limit`/`offset`). Same treatment for `/enrollment-tokens`. Also bound the `InMemoryRateLimiter` bucket dict (evict empty buckets) or move to Redis.

---

## What Is Safe to Ship Right Now

**Solid enough for a controlled / lab / demo deployment (graduation showcase):**
- The **canonical `backend`** core — telemetry ingestion, validation, risk scoring, enrollment-token lifecycle, and the analyst read APIs — is well-architected, fully auth-gated, injection-free, leak-free, and backed by a real 81% test suite incl. an end-to-end flow. It behaves correctly behind a trusted network.
- The **frontend analyst console** — type-clean, builds cleanly, sensible API layer. Fine to demo against a local backend.
- **Secret hygiene in git** is good (nothing sensitive is tracked).

**Must be fixed before any real / internet-facing use:**
- **Enable TLS** (Issue #1) — non-negotiable for telemetry from real devices.
- **Fix the `anas` fail-open token** (Issue #2) — and decide whether `anas/` should even exist; it is a divergent duplicate with weaker security and a broken test harness. Recommend consolidating onto the canonical `backend` and deleting/quarantining `anas/`.
- **Commit lock files + patch the frontend CVEs** (Issue #3).
- **Test the Kafka event pipeline** (0% coverage) before relying on `process_inline=False`, and **unify schema management** on Alembic (drop the `create_all` + ALTER shim) with `PRAGMA foreign_keys=ON` for SQLite.
- **Replace the in-memory rate limiter** and **add pagination** before exposing the analyst APIs to non-trivial data volumes.

**Bottom line:** A strong graduation-project MVP with a genuinely well-tested core backend and clean frontend. It is **not production-ready** as-is — chiefly due to missing TLS, the insecure `anas` duplicate, unpinned dependencies, and an untested async pipeline — but none of these are deep architectural flaws; they are well-scoped, fixable items.
