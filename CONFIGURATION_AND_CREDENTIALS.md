# AEGIS — Configuration & Credentials Guide

This document explains **every** piece of configuration and every credential the AEGIS backend can use: what it's for, whether it's required, where to obtain it, the exact environment-variable name (from `backend/app/config.py`), an example value, where to put it, and how to verify it works.

> **Golden rules**
> 1. **Never commit secrets.** All of these go in `backend/.env` (already git-ignored via `.env` / `.env.*`), or in **GitHub repo secrets** for CI. The repo's `.gitignore` keeps `.env` out of git while allowing `.env.example`.
> 2. **Never paste a real key into a chat or a screenshot.** Put it directly into `backend/.env`.
> 3. **Two profiles:** a **Demo profile** (localhost, almost no external accounts) and a **Production profile** (real DB, Kafka, Redis, TLS, Play Integrity). Each section marks which profile needs it.

---

## 0. How configuration works

- The backend reads settings in `backend/app/config.py` via `load_settings()`, which pulls from **environment variables** with sensible defaults.
- Locally, those env vars come from **`backend/.env`** (loaded by the startup script / your shell). `backend/.env.example` documents the full list; copy it to `.env` and fill in.
- **Precedence:** a real environment variable overrides the `.env` file, which overrides the in-code default.
- After editing `.env`, **restart the backend** for changes to take effect.

| File | Purpose | Committed? |
|------|---------|-----------|
| `backend/.env.example` | Documented template, safe placeholders | ✅ yes |
| `backend/.env` | Your real local values | ❌ never |
| `backend/.env.production.example` | Production template | ✅ yes |

---

## 1. Analyst & enrollment tokens — *self-chosen, REQUIRED*

**What:** AEGIS uses bearer tokens, not passwords. The **analyst token** authenticates the dashboard/console; the **enrollment token** authenticates a device uploading telemetry.
**Required?** Yes (both profiles). **External?** No — *you invent these values.*
**Where to get:** Generate your own. For anything beyond a local demo, use a long random string:
```powershell
# PowerShell — generate a strong random token
[Convert]::ToBase64String((1..32 | % {Get-Random -Max 256}))
```
**Env vars:**
- `AEGIS_ANALYST_TOKENS` — comma-separated list of accepted analyst tokens.
- `AEGIS_ACCEPTED_ENROLLMENT_TOKENS` — comma-separated list of accepted device enrollment tokens.

**Example (`.env`):**
```
AEGIS_ANALYST_TOKENS=analyst-9f3c...long-random
AEGIS_ACCEPTED_ENROLLMENT_TOKENS=enroll-7a21...long-random
```
**Also set on the device:** the Android app's **Settings → Enrollment token** must equal one value in `AEGIS_ACCEPTED_ENROLLMENT_TOKENS`. (In the demo this is `sample-token` on both sides.)
**Verify:** `curl -H "Authorization: Bearer <analyst-token>" http://127.0.0.1:8080/api/v1/devices` returns JSON (not 401).
**Security:** If unset, auth is **fail-closed** (every request is rejected) — that's intentional. Never ship `sample-token` to a real deployment.

---

## 2. Local AI — Ollama — *RECOMMENDED for "real AI", no key*

**What:** Runs the AI threat-analysis models locally (logs / telemetry / risk analyzers). This is the easiest way to make the AI "real" instead of the `stub`.
**Required?** No, but needed if you want genuine AI output without a cloud key. **External?** No account, no key — it's a local service. You already have Ollama installed.
**Where to get:** https://ollama.com (already installed). Then pull a model:
```powershell
ollama pull llama3.1:8b      # or: ollama pull llama3
ollama serve                  # usually auto-starts; serves on 127.0.0.1:11434
```
**Env vars:**
- `AEGIS_LOCAL_LLM_PROVIDER=ollama`  (default is `stub`)
- `AEGIS_LOCAL_LLM_BASE_URL=http://127.0.0.1:11434`
- `AEGIS_LOCAL_LLM_TIMEOUT_SECONDS=120`
- `AEGIS_LOGS_MODEL=llama3.1:8b`
- `AEGIS_TELEMETRY_MODEL=llama3.1:8b`
- `AEGIS_RISK_MODEL=llama3.1:8b`

**Verify:** `curl http://127.0.0.1:11434/api/tags` lists your model; after a scan, `GET /api/v1/ai/runs` shows runs with `provider` ≠ `local_stub`.

---

## 3. Cloud AI — OpenRouter — *OPTIONAL, real API key*

**What:** Powers the **Shieldy analyst chat** and the multi-model orchestrator (orchestrator/critic/report/command roles). Use this instead of, or alongside, Ollama.
**Required?** No (chat returns a clear "not configured" 503 without it). **External?** Yes — an API key from OpenRouter.
**Where to get:** Create an account at https://openrouter.ai → **Keys** → create a key. The project is preconfigured for **free** `deepseek` models, so cost can be \$0.
**Env vars:**
- `OPENROUTER_API_KEY=sk-or-v1-...`  ← the only secret here
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- `OPENROUTER_MODEL=openai/gpt-4o-mini`
- `ORCHESTRATOR_MODEL`, `CRITIC_MODEL`, `GENERAL_MODEL`, `REPORT_MODEL`, `COMMAND_MODEL` — default to `deepseek/deepseek-v4-flash:free`
- `OPENROUTER_TIMEOUT_SECONDS=30`

**Verify:** `POST /api/v1/chat/sessions` then a message returns a real answer (not `chat_not_configured`).
**Security:** Treat the key like a password; rotate it from the OpenRouter dashboard if leaked.

---

## 4. Database — SQLite (default) or PostgreSQL — *password self-chosen*

**What:** Stores telemetry, risk assessments, AI runs, enrollment tokens, feedback.
**Required?** A database is required, but **SQLite is the zero-config default** — nothing to set for the demo. PostgreSQL is for production (Phase 6).
**External?** No external account; for Postgres you **choose** the username/password.
**Env var:** `AEGIS_BACKEND_DATABASE_URL`
- **Demo (default, nothing to set):** `sqlite:///.../backend-data/aegis.db`
- **Production (Postgres):**
  ```
  AEGIS_BACKEND_DATABASE_URL=postgresql+psycopg://aegis:<your-password>@localhost:5432/aegis
  ```
  The `<your-password>` must match what your Postgres (or `docker-compose`) is provisioned with.
**Setup (Postgres):** bring up Postgres (the project's `docker-compose.yml` includes it), then run migrations:
```powershell
cd backend; alembic upgrade head
```
**Verify:** `GET /health` returns `{"ok":true}`; migrations show `alembic current` at head.
**Security:** Use a strong DB password in production; keep it only in `.env` / your secrets manager.

---

## 5. Event pipeline — Kafka — *no credentials locally*

**What:** Optional asynchronous pipeline (API publishes → storage consumer → risk consumer). Default mode is **inline** (synchronous, no Kafka).
**Required?** No. **External?** No — local Docker Kafka needs no credentials.
**Env vars:**
- `AEGIS_PROCESS_INLINE=true` (demo) → set `false` to use Kafka.
- `AEGIS_EVENT_PUBLISHER=none` → set `kafka` to enable.
- `AEGIS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092`
- `AEGIS_KAFKA_TELEMETRY_TOPIC=telemetry_events`
**Setup:** `docker compose up kafka` (from `backend/docker-compose.yml`), then run the consumer process.
**Verify:** with `AEGIS_PROCESS_INLINE=false`, upload telemetry and confirm the consumer logs persist + score it.
**Production auth:** a managed Kafka (SASL/TLS) would add username/password/cert — out of scope for the local setup.

---

## 6. Rate limiting — Redis — *no credentials locally*

**What:** Production-grade rate limiting shared across API replicas (replaces the in-memory limiter).
**Required?** No (in-memory limiter is the default). **External?** No — local Docker Redis has no password by default.
**Env var:** `AEGIS_REDIS_URL=redis://localhost:6379/0`
- Production with auth: `redis://:<password>@host:6379/0`
**Setup:** `docker compose up redis`.
**Verify:** hammer an endpoint past the limit → `429 Too Many Requests`; keys appear in Redis.

---

## 7. Google Play Integrity — backend attestation — *OPTIONAL, heavy external setup*

**What:** Lets the backend verify the Play Integrity token the device sends, turning "Partially verified" into a real "Verified" verdict.
**Required?** No — the service **bypasses gracefully** when unconfigured (returns `REQUIRES_BACKEND_VERIFICATION`). Honestly optional for a graduation demo.
**External?** Yes — this is the most involved credential, requiring Google Cloud + Google Play Console.
**Where to get / steps (follow Google's current docs — labels change):**
1. **Google Play Console:** register the app (package `com.aegis.agent.sample` or your id). Under the app's **App integrity / Play Integrity API**, link a **Google Cloud project**.
2. **Google Cloud Console:** in that project, **enable the "Play Integrity API"**.
3. Create credentials with access to call `decodeIntegrityToken` (a **service account** with the right role, or an API key per your chosen flow).
4. Note your **package name**.
**Env vars:**
- `AEGIS_GOOGLE_PLAY_INTEGRITY_API_KEY=<from Google Cloud>`
- `AEGIS_GOOGLE_PLAY_INTEGRITY_PACKAGE_NAME=com.aegis.agent.sample`
**Verify:** a real device/Play-linked build sends a token; `GET /api/v1/devices/<id>/latest-risk` shows a `MEETS_*`/`FAILS` verdict instead of "partially verified".
**Note for the defense:** on a plain emulator without Play services this won't return a full verdict — that's expected. Document it as "requires a Play-linked build / real device."
**Security:** store the service-account JSON / API key only in `.env` or a secrets manager; never in git or the APK.

---

## 8. HTTPS / TLS certificate — *production only*

**What:** Serves the API/dashboard over HTTPS via nginx (Phase 3/10). The audit flagged that `nginx.conf` listened on port 80 only.
**Required?** Production only — not needed on localhost.
**External?** A certificate: free from **Let's Encrypt** for a real domain, or **self-signed** for a demo box.
**Where to get:**
- Real domain: `certbot` (Let's Encrypt) → `fullchain.pem` + `privkey.pem`.
- Demo/self-signed (PowerShell/OpenSSL):
  ```
  openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
  ```
**Where to put:** mount the cert/key into nginx and point the `ssl_certificate` / `ssl_certificate_key` directives at them; add the 443 server block + an 80→443 redirect.
**Verify:** `https://<host>/` loads with a valid (or accepted self-signed) certificate; HTTP redirects to HTTPS.

---

## 9. CI/CD secrets — GitHub Actions — *only if pushing images*

**What:** The repo has `.github/workflows/ci.yml` (ruff · mypy · pytest · vite build — **needs no secrets**) and `docker-push.yml` (builds/pushes images — **needs registry creds**).
**Required?** Only if you actually push Docker images. The test/lint CI runs with nothing extra.
**External?** Yes — a container-registry token (Docker Hub or GitHub Container Registry).
**Where to put:** **GitHub → repo → Settings → Secrets and variables → Actions → New repository secret.** Never in `.env` or code.
- Docker Hub: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (create the token in Docker Hub → Account Settings → Security).
- GHCR: usually the built-in `GITHUB_TOKEN` with `packages: write` permission.
**Verify:** the `docker-push` workflow run succeeds and the image appears in the registry.

---

## 10. Android release signing keystore — *only for a release APK*

**What:** Signs a **release** build of the agent app. The demo uses the **debug** build, which is auto-signed — so this is not needed for the demo.
**Required?** Only to produce a distributable release APK/AAB.
**External?** No — you generate the keystore yourself.
**Where to get:**
```
keytool -genkey -v -keystore aegis-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias aegis
```
**Where to put:** reference it in `aegis-agent/app/build.gradle.kts` signing config via **`local.properties`** or env (keep the keystore + passwords out of git).
**Verify:** `./gradlew :app:assembleRelease` produces a signed APK.

---

## 11. Other tunables (no credentials)

| Env var | Purpose | Default |
|---------|---------|---------|
| `AEGIS_RAW_PAYLOAD_DIR` | Where raw telemetry JSON is stored | `backend-data/raw-payloads` |
| `AEGIS_TELEMETRY_RATE_LIMIT_MAX_REQUESTS` | Telemetry rate-limit count | `120` |
| `AEGIS_TELEMETRY_RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window | `60` |
| `AEGIS_WORKER_POLL_INTERVAL_SECONDS` | Worker poll cadence | `5` |
| `AEGIS_CORS_ALLOWED_ORIGINS` | Dashboard origins allowed | `http://127.0.0.1:5173,http://localhost:5173` |

---

## 12. Ready-to-fill `.env` templates

### Demo profile — copy to `backend/.env` (only Ollama needs a one-time `ollama pull`)
```
# --- Auth (invent your own; app enrollment token must match) ---
AEGIS_ANALYST_TOKENS=sample-token
AEGIS_ACCEPTED_ENROLLMENT_TOKENS=sample-token

# --- AI via local Ollama (no key) ---
AEGIS_LOCAL_LLM_PROVIDER=ollama
AEGIS_LOCAL_LLM_BASE_URL=http://127.0.0.1:11434
AEGIS_LOGS_MODEL=llama3.1:8b
AEGIS_TELEMETRY_MODEL=llama3.1:8b
AEGIS_RISK_MODEL=llama3.1:8b

# --- Everything else uses safe local defaults ---
AEGIS_PROCESS_INLINE=true
AEGIS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

# --- OPTIONAL cloud AI (leave blank to skip) ---
OPENROUTER_API_KEY=
```

### Production profile — copy to `backend/.env` (fill the <PLACEHOLDERS>)
```
AEGIS_ANALYST_TOKENS=<long-random-analyst-token>
AEGIS_ACCEPTED_ENROLLMENT_TOKENS=<long-random-enrollment-token>

AEGIS_BACKEND_DATABASE_URL=postgresql+psycopg://aegis:<db-password>@postgres:5432/aegis

AEGIS_PROCESS_INLINE=false
AEGIS_EVENT_PUBLISHER=kafka
AEGIS_KAFKA_BOOTSTRAP_SERVERS=kafka:9092
AEGIS_REDIS_URL=redis://redis:6379/0

# AI — pick Ollama or OpenRouter
AEGIS_LOCAL_LLM_PROVIDER=ollama
OPENROUTER_API_KEY=<sk-or-... or leave blank>

# Play Integrity (optional, real attestation)
AEGIS_GOOGLE_PLAY_INTEGRITY_API_KEY=<google-cloud-key>
AEGIS_GOOGLE_PLAY_INTEGRITY_PACKAGE_NAME=com.aegis.agent.sample
```

---

## 13. Quick "what do I actually need?" summary

| Thing | Demo | Production | External account? | Secret? |
|-------|------|-----------|-------------------|---------|
| Analyst/enrollment tokens | ✅ (you pick) | ✅ strong values | No | Yes |
| Ollama model | ✅ `ollama pull` | optional | No | No |
| OpenRouter key | optional | optional | Yes (openrouter.ai) | Yes |
| PostgreSQL | – (SQLite) | ✅ | No (you set pwd) | Yes (pwd) |
| Kafka | – | ✅ | No (local) | No (local) |
| Redis | – | ✅ | No (local) | No (local) |
| Play Integrity | – | optional | Yes (Google Cloud + Play Console) | Yes |
| TLS certificate | – | ✅ | Let's Encrypt / self-signed | Yes (key) |
| CI registry token | – | if pushing images | Yes (Docker Hub/GHCR) | Yes (GitHub secret) |
| Android keystore | – | release builds only | No | Yes |

**Bottom line:** for a full graduation **demo with real AI**, the only action is `ollama pull llama3.1:8b`. Every other credential is optional or production-only.
