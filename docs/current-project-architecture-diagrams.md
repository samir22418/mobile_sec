# Current Project Architecture Diagrams

This page captures the current practical MVP architecture after the backend,
logs, dashboard, and AI integration work. It is intentionally simpler than the
future production architecture.

## System Context

```mermaid
flowchart LR
  Emulator["Android Emulator / Device"]
  Agent["AEGIS Android Agent"]
  API["FastAPI Backend"]
  DB[("SQLite local DB\nPostgres-compatible schema")]
  Raw["Filesystem raw payloads"]
  Worker["Local normalization worker"]
  Rules["Deterministic risk rules"]
  LocalAI["Local AI analyzer interface\nstub or Ollama-compatible"]
  Dashboard["Streamlit Dashboard"]
  Chat["Shieldy Chatbot\nOpenRouter only"]

  Emulator --> Agent
  Agent -->|"POST /api/v1/telemetry"| API
  API --> DB
  API --> Raw
  API --> Worker
  Worker --> Rules
  Rules --> LocalAI
  LocalAI --> DB
  Dashboard -->|"Bearer analyst token"| API
  Chat -->|"redacted selected context"| API
```

## Android To Backend Flow

```mermaid
sequenceDiagram
  participant User as Analyst / Tester
  participant App as Android Sample App
  participant SDK as AEGIS Agent SDK
  participant API as FastAPI API
  participant Worker as Local Worker
  participant DB as SQLite DB

  User->>App: Run Security Scan
  App->>SDK: Collect posture, apps, integrity state, important logs
  SDK->>App: Persist scan record and upload state
  App->>API: POST telemetry with enrollment token
  API->>API: Validate schema and idempotency
  API->>DB: Store telemetry payload row
  API->>API: Store raw JSON on disk
  API->>Worker: Trigger local processing
  Worker->>DB: Normalize device report, app inventory, logs
  Worker->>DB: Store baseline and AI final risk outputs
  API-->>App: 202 Accepted
```

## Backend Processing And AI Flow

```mermaid
flowchart TD
  Payload["Telemetry payload"]
  Validate["Schema validation + body-token auth"]
  RawStore["Raw JSON storage"]
  Normalize["Normalize posture, apps, logs"]
  Redact["Redact logs + hash messages"]
  Baseline["Rule-based baseline score"]
  LogsAI["logs_llm_analyst"]
  TelemetryAI["telemetry_llm_analyst"]
  RiskAI["risk_llm_scorer"]
  Decision["AI risk decision"]
  Fallback["Fallback to deterministic result"]
  Audit["ai_model_runs audit records"]

  Payload --> Validate --> RawStore --> Normalize
  Normalize --> Redact --> Baseline
  Baseline --> LogsAI --> Audit
  Baseline --> TelemetryAI --> Audit
  LogsAI --> RiskAI
  TelemetryAI --> RiskAI
  Baseline --> RiskAI
  RiskAI -->|"valid JSON + evidence refs"| Decision
  RiskAI -->|"invalid output"| Fallback
  Decision --> Audit
  Fallback --> Audit
```

## Dashboard And Analyst Flow

```mermaid
flowchart LR
  Analyst["Analyst"]
  UI["Streamlit Dashboard"]
  Devices["Devices + Payload Detail"]
  Logs["Logs Analyzer"]
  AICenter["AI Center"]
  Shieldy["Shieldy Chat"]
  API["FastAPI API"]
  Audit[("AI runs, actions, feedback")]

  Analyst --> UI
  UI --> Devices
  UI --> Logs
  UI --> AICenter
  UI --> Shieldy
  Devices --> API
  Logs --> API
  AICenter --> API
  Shieldy -->|"selected redacted payload context"| API
  API --> Audit
```

## Data Ownership

```mermaid
erDiagram
  telemetry_payloads ||--o{ device_reports : normalizes
  telemetry_payloads ||--o{ app_inventory_current : updates
  telemetry_payloads ||--o{ important_logs : redacts
  telemetry_payloads ||--o{ risk_assessments : scores
  telemetry_payloads ||--o{ ai_model_runs : audits
  telemetry_payloads ||--o| ai_risk_decisions : finalizes
  telemetry_payloads ||--o{ analyst_feedback : reviews
  chat_sessions ||--o{ chat_messages : contains
  chat_messages ||--o{ chat_actions : proposes
```

## Current Gaps To Keep Visible

- Local MVP uses SQLite and `create_all`; production needs verified Alembic
  migrations against Postgres.
- OpenRouter is intentionally limited to Shieldy Chat, and requires a real
  `OPENROUTER_API_KEY`.
- Local analyzers are replaceable stubs unless configured for a real local model
  runtime.
- Android log visibility depends on device policy, debug state, and OS limits;
  the backend must accept empty `important_logs`.
- Streamlit is acceptable for MVP speed, but a React/Vite dashboard becomes
  better once workflow density and role-based UX grow.
