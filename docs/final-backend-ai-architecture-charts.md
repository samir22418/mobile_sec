# AEGIS Final Backend Architecture Charts

Rendered artifacts:

```text
docs/final-backend-ai-architecture.pdf
docs/generated/final-backend-ai-architecture/*.png
```

Renderer:

```text
tools/render_final_backend_ai_architecture.py
```

## 1. Final Backend Overview

```mermaid
flowchart TD
  Agent["Android Agent"] --> API["Backend Ingestion API"]
  API --> Raw["Raw Payload Store"]
  API --> Queue["Processing Queue"]
  Queue --> Worker["Telemetry Worker"]
  Worker --> DB["PostgreSQL Operational DB"]
  Worker --> Risk["Risk + AI Engine"]
  Risk --> Assess["Risk Assessments"]
  Assess --> Dashboard["Dashboard / Alerts / API"]
```

## 2. Processing Flow

```mermaid
flowchart LR
  Upload["Upload"] --> Validate["Validate + Idempotency"]
  Validate --> Store["Store Raw"]
  Store --> Normalize["Normalize"]
  Normalize --> Redact["Redact Logs"]
  Redact --> Features["Extract Features"]
  Features --> Score["Rules + AI"]
  Score --> Result["Final Assessment"]
```

## 3. Risk + AI Flow

```mermaid
flowchart TD
  Features["Features + Evidence"] --> Rules["Rules Always Run"]
  Rules --> Suspicious{"Suspicious?"}
  Suspicious -- "No" --> FinalLow["Store Low Risk"]
  Suspicious -- "Yes" --> LLM["Primary LLM Analyst"]
  LLM --> Critical{"Critical or Ambiguous?"}
  Critical -- "No" --> Fusion["Evidence Fusion"]
  Critical -- "Yes" --> Reviewer["Reviewer LLM"]
  Reviewer --> Fusion
  Fusion --> Final["Final Risk + Reasons"]
```

## 4. Minimal Data Model

```mermaid
flowchart LR
  Payloads["telemetry_payloads"] --> Device["device_reports"]
  Payloads --> Apps["app_inventory_current"]
  Payloads --> Logs["important_logs"]
  Device --> Risk["risk_assessments"]
  Apps --> Risk
  Logs --> Risk
  Risk --> Runs["ai_model_runs"]
  Risk --> Feedback["analyst_feedback"]
```

