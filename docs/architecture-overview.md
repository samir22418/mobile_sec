# AEGIS — System Architecture Overview

## High-level data flow

```
Android Device
  │
  │  1. DeviceScanner.scan()
  │     ├─ RootDetector
  │     ├─ AppInventoryScanner
  │     ├─ LogFilterAgent (logcat → ImportanceFilter)
  │     └─ IntegrityApiClient  ──→  Google Play Integrity API
  │         returns: token + nonce
  │
  │  2. WorkManager upload (RetryPolicy, ACCEPTED / PROCESSED)
  │
  ▼
nginx (TLS 443) ──→ FastAPI API (port 8080)
                        │
                        │  POST /api/v1/telemetry
                        │  ├─ Auth: Bearer token (constant-time compare)
                        │  ├─ Rate limit: RedisRateLimiter (sliding window)
                        │  ├─ Schema validation (JSON Schema v1)
                        │  ├─ Redaction (tokens / emails / PII stripped)
                        │  └─ Raw payload → disk (RawPayloadStore)
                        │
                   ┌────┴─────────────────────────────────┐
                   │  process_inline=true (dev)            │
                   │  process_inline=false (prod)          │
                   └───────────────┬─────┬────────────────┘
                                   │     │
                     inline path ──┘     └── Kafka topic: telemetry_events
                          │                       │
                          │              TelemetryConsumer (consumer group)
                          │                       │
                          ▼                       ▼
                    TelemetryWorker ◄─────────────┘
                          │
                          ├─ 1. NormalizationService
                          │      saves: DeviceReport, AppSnapshot, ImportantLog
                          │
                          ├─ 2. PlayIntegrityService
                          │      POST googleapis.com/v1/{pkg}:decodeIntegrityToken
                          │      nonce/replay check → verified_integrity_verdict
                          │
                          ├─ 3. RiskScoringService
                          │      rule-based score (0–100)
                          │      → RiskAssessment (score, label, reasons)
                          │
                          └─ 4. AIAnalysisService  (if score ≥ threshold)
                                 ├─ build_evidence_bundle()
                                 ├─ log_triage_model
                                 ├─ app_reputation_model
                                 ├─ posture_model
                                 ├─ primary_llm_analyst  (OpenRouter / Ollama)
                                 ├─ reviewer_llm
                                 └─ evidence_fusion → AIRiskDecision + AIFindings
```

## Persistence layer (Postgres / SQLite)

| Table | Contents |
|---|---|
| `telemetry_payloads` | One row per upload; tracks `processing_status` |
| `device_reports` | Normalised device posture + `verified_integrity_verdict` |
| `app_snapshots` / `installed_apps` | App inventory per scan |
| `important_logs` | Pre-filtered log signals |
| `risk_assessments` | Rule-based score, label, reasons |
| `ai_model_runs` | One row per LLM sub-call; status SUCCEEDED / FAILED |
| `ai_risk_decisions` | Final AI verdict + `used_ai_final` flag |
| `ai_findings` | Per-finding rows with evidence refs |
| `ai_evidence_bundles` | Serialised evidence bundle sent to the LLM |
| `enrollment_tokens` | Device enrolment token registry |
| `feedback` | Analyst feedback on risk decisions |

## Services and their dependencies

```
FastAPI app
  ├─ IngestionService
  │    └─ TelemetryWorker (inline) or KafkaProducer (async)
  ├─ AuthService          — enrollment + analyst token management
  ├─ TelemetryValidationService — JSON Schema
  ├─ RedisRateLimiter     — sliding-window; falls back to InMemoryRateLimiter
  └─ PlayIntegrityService — calls Google API; no-op when unconfigured

Consumer process (Dockerfile.consumer)
  └─ TelemetryConsumer    — Kafka consumer with retry + DLQ
       └─ TelemetryWorker (same logic as inline path)
```

## Infrastructure (docker-compose)

```
nginx (80/443, TLS)
  ├── api (FastAPI, 8080)
  │     ├── postgres (5432)
  │     ├── kafka  ←── zookeeper (2181)
  │     └── redis  (6379)
  ├── worker (TelemetryConsumer)
  │     ├── postgres
  │     └── kafka
  └── dashboard (React/Vite, served by nginx on 5173→80)
```

## Play Integrity attestation flow

1. Android app requests integrity token with `deviceId:timestamp` nonce.
2. `DeviceReport` payload includes `integrity_token` + `integrity_nonce`.
3. Backend `TelemetryWorker._verify_play_integrity()`:
   - Checks nonce is not already seen in a different payload (replay guard).
   - Calls `https://playintegrity.googleapis.com/v1/{pkg}:decodeIntegrityToken`.
   - Maps `deviceRecognitionVerdict` array → single string verdict.
   - Stores result as `verified_integrity_verdict` on `DeviceReport`.
4. `RiskScoringService` uses `verified_integrity_verdict` (preferred) or falls back to `integrity_verdict`.

Verdict precedence: `MEETS_STRONG_INTEGRITY` > `MEETS_DEVICE_INTEGRITY` > `MEETS_BASIC_INTEGRITY` > `FAILS`.

## Rate limiting

`RedisRateLimiter` uses a sorted-set sliding window (ZADD + ZREMRANGEBYSCORE + ZCARD + EXPIRE) inside a `MULTI/EXEC` pipeline — atomic across replicas. Falls back to `InMemoryRateLimiter` when Redis is unreachable. Applied to both `/api/v1/telemetry` and auth/enrollment endpoints.

## AI analysis pipeline

Only runs when `risk_score ≥ AI_THRESHOLD` (default 40). Five sub-models:

| Role | Input | Output |
|---|---|---|
| `log_triage_model` | Log signals | High-severity log findings |
| `app_reputation_model` | Sideloaded / high-perm apps | App risk findings |
| `posture_model` | Root / bootloader / patch / integrity | Posture findings |
| `primary_llm_analyst` | All evidence | Synthesised findings |
| `reviewer_llm` | Primary output | Critique / rejection |
| `evidence_fusion` | All model outputs | Final decision + score |

Provider: `openrouter` (production) or `ollama` (local). Graceful fallback to `StubLocalAnalyzerProvider` on any provider error.
