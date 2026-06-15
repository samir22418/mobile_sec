# AEGIS AI/LLM Threat Analysis Charts

These charts visualize the AI architecture for malicious app data, device
posture, and important log analysis.

Rendered artifacts:

```text
docs/ai-llm-threat-analysis-charts.pdf
docs/generated/ai-llm-charts/*.png
```

Renderer:

```text
tools/render_ai_llm_charts.py
```

## 1. AI Analysis System Overview

```mermaid
flowchart TD
  Agent["Android Agent Telemetry"] --> Ingest["Telemetry Ingestion API"]
  Ingest --> Raw["Raw Payload Store"]
  Ingest --> Queue["Processing Queue"]

  Queue --> Normalize["Normalize Device / Apps / Logs"]
  Normalize --> Redact["Redact PII, Secrets, Tokens"]
  Redact --> Enrich["Threat Intel + Policy Enrichment"]
  Enrich --> Features["Feature Extraction"]

  Features --> Rules["Deterministic Rule Engine"]
  Features --> Specialist["Specialist Models"]
  Features --> Router["AI Model Router"]

  Specialist --> LogModel["Log Triage Model"]
  Specialist --> AppModel["App Reputation Model"]
  Specialist --> PostureModel["Posture Reasoning Model"]

  Router --> PrimaryLLM["Primary LLM Analyst"]
  Router --> ReviewerLLM["Independent Reviewer LLM"]
  Router --> Summarizer["Finding Summarizer"]

  Rules --> Fusion["Evidence Fusion"]
  LogModel --> Fusion
  AppModel --> Fusion
  PostureModel --> Fusion
  PrimaryLLM --> Fusion
  ReviewerLLM --> Fusion

  Fusion --> Assessment["Final AI Assessment"]
  Assessment --> Findings["Evidence-Backed Findings"]
  Assessment --> Score["Risk Score + Confidence"]
  Assessment --> Actions["Recommended Actions"]
  Assessment --> Review["Human Review Queue"]

  Findings --> Dashboard["SOC / Admin Dashboard"]
  Score --> Dashboard
  Actions --> Dashboard
```

## 2. Model Router Decision Chart

```mermaid
flowchart TD
  Start["Feature Vector + Evidence Bundle"] --> RuleScore["Compute Rule Score"]
  RuleScore --> Critical{"Critical deterministic signal?"}

  Critical -- "Yes" --> HighPath["High-Risk Route"]
  Critical -- "No" --> MediumCheck{"Suspicious apps/logs or threat-intel hits?"}

  MediumCheck -- "No" --> LowPath["Low-Risk Route"]
  MediumCheck -- "Yes" --> AmbiguousCheck{"Ambiguous or conflicting evidence?"}

  AmbiguousCheck -- "No" --> MediumPath["Medium-Risk Route"]
  AmbiguousCheck -- "Yes" --> ReviewPath["Ambiguous Route"]

  LowPath --> LowModels["Rules + Specialist Models"]
  MediumPath --> MediumModels["Rules + Specialist Models + Primary LLM"]
  HighPath --> HighModels["Rules + Specialist Models + Primary LLM + Reviewer LLM"]
  ReviewPath --> ReviewModels["Primary LLM + Reviewer LLM + Human Review"]

  LowModels --> Fuse["Evidence Fusion"]
  MediumModels --> Fuse
  HighModels --> Fuse
  ReviewModels --> Fuse

  Fuse --> Final["Final Risk Score + Findings"]
```

## 3. AI Analysis Sequence

```mermaid
sequenceDiagram
  participant Worker as Telemetry Worker
  participant Redactor as Redaction Service
  participant Builder as Evidence Builder
  participant Router as Model Router
  participant Rules as Rule Engine
  participant Small as Specialist Models
  participant LLM1 as Primary LLM
  participant LLM2 as Reviewer LLM
  participant Fusion as Evidence Fusion
  participant Store as AI Findings Store
  participant SOC as Dashboard

  Worker->>Redactor: normalized device, app, and log evidence
  Redactor->>Builder: sanitized evidence
  Builder->>Router: bounded evidence bundle + feature vector
  Router->>Rules: run deterministic checks
  Rules-->>Fusion: rule score + reason codes
  Router->>Small: classify logs, apps, posture signals
  Small-->>Fusion: labels + confidence
  Router->>LLM1: analyze suspicious evidence bundle
  LLM1-->>Fusion: findings + evidence refs
  Router->>LLM2: review high-risk or ambiguous case
  LLM2-->>Fusion: objections + agreement state
  Fusion->>Store: final assessment, findings, model runs
  Store->>SOC: score, reasons, recommended action
```

## 4. Evidence And Storage Lineage

```mermaid
flowchart LR
  Raw["raw_telemetry_json"] --> Payloads["telemetry_payloads"]
  Payloads --> Device["device_reports"]
  Payloads --> Apps["app_snapshots"]
  Payloads --> Logs["important_logs"]

  Apps --> CurrentInv["app_inventory_current"]
  Apps --> AppEvents["app_inventory_events"]

  Device --> Features["risk_features"]
  CurrentInv --> Features
  AppEvents --> Features
  Logs --> Features

  Features --> Bundle["ai_evidence_bundles"]
  Bundle --> ModelRuns["ai_model_runs"]
  ModelRuns --> Findings["ai_findings"]
  Findings --> Final["ai_final_assessments"]
  Final --> Feedback["ai_feedback_labels"]

  Feedback --> Eval["evaluation_datasets"]
  Eval --> Registry["model_registry + prompt_registry"]
  Registry --> ModelRuns
```

## 5. AI Deployment Topology

```mermaid
flowchart TD
  API["Ingestion API"] --> DB["PostgreSQL Operational DB"]
  API --> ObjectStore["Raw Object Storage"]
  API --> MainQueue["Telemetry Processing Queue"]

  MainQueue --> TelemetryWorkers["Telemetry Worker Pool"]
  TelemetryWorkers --> DB
  TelemetryWorkers --> AIQueue["AI Analysis Queue"]

  AIQueue --> AIWorkers["AI Worker Pool"]
  AIWorkers --> Router["Model Router"]

  Router --> LocalModels["Private / Local Models"]
  Router --> ProviderA["LLM Provider A"]
  Router --> ProviderB["LLM Provider B"]
  Router --> Specialist["Specialist Classifiers"]

  Router --> ModelRuns["Model Run Store"]
  ModelRuns --> Fusion["Evidence Fusion"]
  Fusion --> FindingsDB["AI Findings DB"]
  FindingsDB --> Dashboard["SOC Dashboard"]
  FindingsDB --> Alerting["Alert/Event Stream"]
  FindingsDB --> Warehouse["Warehouse / Lakehouse"]

  Dashboard --> Feedback["Analyst Feedback"]
  Feedback --> Evaluation["Evaluation + Retraining"]
  Evaluation --> Registry["Model + Prompt Registry"]
  Registry --> Router
```

## 6. Human Review Loop

```mermaid
flowchart TD
  Assessment["Final AI Assessment"] --> NeedsReview{"Needs human review?"}
  NeedsReview -- "No" --> AutoClose["Store + Show in Dashboard"]
  NeedsReview -- "Yes" --> AnalystQueue["Analyst Review Queue"]

  AnalystQueue --> Analyst["Security Analyst"]
  Analyst --> Label{"Analyst label"}

  Label -- "True positive" --> TP["Confirm Finding"]
  Label -- "False positive" --> FP["Suppress / Tune Rules"]
  Label -- "Benign" --> Benign["Update Allowlist / Policy Context"]
  Label -- "Needs more data" --> MoreData["Request Enrichment or New Scan"]

  TP --> Feedback["ai_feedback_labels"]
  FP --> Feedback
  Benign --> Feedback
  MoreData --> Feedback

  Feedback --> Metrics["Evaluation Metrics"]
  Metrics --> PromptTune["Prompt / Model / Rule Updates"]
  PromptTune --> Registry["Model + Prompt Registry"]
```
