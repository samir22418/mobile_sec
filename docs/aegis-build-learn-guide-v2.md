AEGIS — Android Enterprise Guard & Intelligence Security  |  Build & Learn Guide v2

**AEGIS**

Android Enterprise Guard & Intelligence Security

PROJECT BUILD PROMPT SEQUENCE  —  v2 Simplified Architecture

|**Document Type**|Build & Learn Guide — Simplified Architecture|
| :- | :- |
|**Phases**|5 Build Phases (Dynamic Analysis removed)|
|**Total Prompts**|15 Prompts + 15 Checkpoints|
|**Stack**|Kotlin · Python · FastAPI · Kafka · React · Claude API|
|**Key Change**|All device data moves as JSON → Server first|
|**Analysis**|Static Engine + AI CLI run in parallel (same phase)|
|**Logs**|Streaming — important logs only, AI agent processes them|
|**Dynamic**|Removed — can be added later if needed|

## **HOW TO USE THIS DOCUMENT**
Each section contains (1) a BUILD PROMPT to give Claude to generate code, followed by (2) an UNDERSTANDING CHECKPOINT to help you fully learn what was built. Phases are ordered — complete each phase before starting the next. The two parallel tracks in Phase 3 should be started at the same time.

|**PH 01**|<p>**Foundation — Kotlin Android Agent**</p><p>⏱ Weeks 1–4</p>|
| :-: | :- |

Build the core EDR agent running on every enrolled device. The agent collects device security data, app intelligence, and filters logs — then ships everything as JSON to the server.

## **Prompt 1.1 — Project Scaffold & Gradle Setup**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>You are a senior Android engineer. Scaffold a production-grade Android library</p><p>module named "aegis-agent" using Kotlin and Gradle (Kotlin DSL).</p><p></p><p>Requirements:</p><p>- minSdk 26, targetSdk 34</p><p>- Hilt for dependency injection</p><p>- WorkManager for scheduled background jobs</p><p>- Kotlin Coroutines + Flow</p><p>- OkHttp 4.x with certificate pinning support (mTLS)</p><p>- kotlinx.serialization for JSON</p><p>- Timber for logging</p><p></p><p>Output: build.gradle.kts, settings.gradle.kts, AndroidManifest.xml,</p><p>base Application class with Hilt, and a README with module structure.</p><p>Use clean architecture: data / domain / presentation layers.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 1.2 — DeviceScanner Module**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Using the aegis-agent scaffold, implement a DeviceScanner Kotlin class</p><p>inside agent/data/scanner/. It must:</p><p></p><p>1\. Detect root using 3 methods:</p><p>`   `a. Check for su binary in common paths</p><p>`   `b. Check Build.TAGS for "test-keys"</p><p>`   `c. Check if /system/app/Superuser.apk exists</p><p></p><p>2\. Query the Play Integrity API and return:</p><p>`   `MEETS\_STRONG\_INTEGRITY / MEETS\_DEVICE\_INTEGRITY /</p><p>`   `MEETS\_BASIC\_INTEGRITY / FAILS</p><p></p><p>3\. Read android.os.Build.VERSION.SECURITY\_PATCH</p><p>4\. Read bootloader state from SystemProperties</p><p></p><p>Return a DeviceReport data class serialized as JSON.</p><p>All functions must be suspending (coroutines, NOT callbacks).</p><p>Add unit tests using JUnit5 + Mockk.</p>|
| :- |

|<p>**🔐  Security Note**</p><p>Play Integrity API is the most reliable signal — treat it as primary. Binary checks (su path) are supplementary. Rooted devices with Magisk Hide will defeat binary checks.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 1.3 — App Intelligence Collector**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Implement AppIntelligenceCollector.kt in agent/data/apps/. It must:</p><p></p><p>1\. List all installed packages via PackageManager</p><p>`   `- Filter out system packages ONLY for BYOD mode (add a mode flag)</p><p></p><p>2\. For each package collect:</p><p>`   `- packageName, versionName, versionCode</p><p>`   `- SHA-256 of the base APK file</p><p>`   `- Signing certificate SHA-256</p><p>`   `- List of requested permissions</p><p>`   `- installSource (Play Store / sideloaded / MDM)</p><p></p><p>3\. Register a BroadcastReceiver for ACTION\_PACKAGE\_ADDED and</p><p>`   `ACTION\_PACKAGE\_REMOVED — emit changes as a Flow<PackageEvent></p><p></p><p>4\. Store last-known app list in DataStore<Preferences> for delta diffing.</p><p>`   `Only report CHANGED apps on subsequent scans (bandwidth optimisation).</p><p></p><p>Return AppSnapshot data class serialized as JSON. Add KDoc on all public APIs.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 1.4 — Log Filter Agent**
This is a new module specific to AEGIS v2. The device never sends all logs to the server — only important ones.

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Implement a LogFilterAgent.kt in agent/data/logs/.</p><p></p><p>Requirements:</p><p>1\. Monitor Android logcat output in real-time using a coroutine + Flow pipeline</p><p>2\. Define an ImportanceFilter that passes only logs matching these criteria:</p><p>`   `- Log tag contains: SECURITY, AUTH, CRASH, ANOMALY, VIOLATION, PERMISSION</p><p>`   `- Log level is ERROR or ASSERT (Log.e, Log.wtf)</p><p>`   `- Message matches a threat regex list:</p><p>`     `\* "permission denied", "root", "injection", "exploit",</p><p>`     `\* "brute force", "failed login", "certificate error"</p><p>3\. Discard all other logs immediately — never store or buffer them</p><p>4\. Buffer passing logs in a local in-memory queue (max 200 entries, 10-minute TTL)</p><p>5\. Serialize filtered logs as ImportantLog data class:</p><p>`   `timestamp, deviceId, tag, level, message, matchedRule</p><p>6\. Expose a Flow<List<ImportantLog>> that flushes the buffer every 30 seconds</p><p>`   `(or immediately if ≥ 50 entries accumulate)</p><p></p><p>Add unit tests with mock logcat input.</p>|
| :- |

|<p>**🔐  Security Note**</p><p>Never send raw logcat to the server. Only pre-filtered important logs leave the device. This protects user privacy and keeps bandwidth low.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

|**PH 02**|<p>**Server Ingestion — All JSON Arrives Here First**</p><p>⏱ Weeks 5–7</p>|
| :-: | :- |

The server is the single entry point for all device data. Every piece of information from the agent arrives as JSON here before being routed to analysis, storage, or Kafka topics.

## **Prompt 2.1 — FastAPI Ingestion Gateway**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build a production-grade FastAPI ingestion service in Python 3.11.</p><p></p><p>Endpoints (all receive JSON):</p><p>- POST /api/v1/telemetry      — DeviceReport JSON (device posture)</p><p>- POST /api/v1/apps           — AppSnapshot JSON (app intelligence)</p><p>- POST /api/v1/logs           — ImportantLogs JSON array (filtered device logs)</p><p>- POST /api/v1/apk/upload     — APK binary (multipart), validate magic bytes</p><p>- GET  /health</p><p>- GET  /metrics               — Prometheus</p><p></p><p>Security:</p><p>- mTLS: verify device identity via client certificate, extract device\_id from CN field</p><p>- Rate limit: 10 requests/minute per device\_id (use slowapi)</p><p>- Validate all JSON with Pydantic v2 schemas</p><p>- Never log raw payload contents (contains device fingerprints)</p><p></p><p>On receipt:</p><p>- Telemetry + Apps → save to PostgreSQL + publish to Kafka "device.telemetry"</p><p>- APK → save to MinIO/S3, publish to Kafka "apk.analysis"</p><p>- Logs → publish directly to Kafka "logs.stream"</p><p>- If device risk flag exists in DB → also publish to "device.flagged"</p><p></p><p>Include docker-compose.yml: FastAPI + Kafka + Zookeeper + MinIO + PostgreSQL + Redis</p><p>Include .env.example and pytest tests for all endpoints.</p>|
| :- |

|<p>**🔐  Security Note**</p><p>The server is the single source of truth. All device data must pass through here. Kafka routing happens server-side — the device agent only needs one HTTPS endpoint per data type.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 2.2 — Kafka Topics & Schema Registry**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Design and implement the Kafka topic architecture for AEGIS v2.</p><p></p><p>Topics:</p><p>- device.telemetry  (partitions: 12, retention: 7 days)</p><p>- apk.analysis      (partitions: 6,  retention: 30 days)</p><p>- logs.stream       (partitions: 12, retention: 24 hours — important logs only)</p><p>- risk.scores       (partitions: 6,  retention: 90 days)</p><p>- response.actions  (partitions: 3,  retention: 7 days)</p><p>- device.flagged    (partitions: 6,  retention: 30 days)</p><p></p><p>Using the Confluent Kafka Python client and Avro schemas:</p><p>1\. Write Avro schemas for: DeviceTelemetry, AppSnapshot, ImportantLog, RiskScore</p><p>2\. Create topic\_admin.py script to create/update all topics</p><p>3\. Create a base KafkaConsumer class with:</p><p>`   `- At-least-once delivery</p><p>`   `- Dead letter queue on 3 failures</p><p>`   `- Graceful shutdown on SIGTERM</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

|**PH 03**|<p>**Analysis — Static Engine + AI CLI Agent (Parallel)**</p><p>⏱ Weeks 8–12</p>|
| :-: | :- |

Both tracks run simultaneously on the same APK. The Python static engine is fast and deterministic (rules, regex, entropy). The AI CLI agent catches subtle logic threats that rules miss. Their outputs are merged into one StaticReport.

## **Prompt 3.1 — Python Static Analysis Engine**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build a Python static analysis engine for Android APKs.</p><p>It consumes the "apk.analysis" Kafka topic.</p><p></p><p>Architecture:</p><p>1\. APKUnpacker: download APK from MinIO, unpack with apktool,</p><p>`   `decompile with jadx into a temp directory</p><p></p><p>2\. SecretDetector: scan all smali + decompiled Java/Kotlin source for:</p><p>`   `- API keys (regex patterns for AWS, Google, Stripe, etc.)</p><p>`   `- High-entropy strings (Shannon entropy > 4.5 on strings > 20 chars)</p><p>`   `- Hardcoded IPs and URLs</p><p></p><p>3\. PermissionAnalyzer: parse AndroidManifest.xml, score each permission</p><p>`   `using a risk matrix (DANGEROUS > SIGNATURE > NORMAL)</p><p></p><p>4\. TrackerDetector: match package names against Exodus Privacy tracker DB</p><p></p><p>5\. ObfuscationDetector: measure average identifier length in class names</p><p>`   `(< 3 chars average = likely obfuscated)</p><p></p><p>6\. StaticReport dataclass: aggregate all findings with severity scores</p><p></p><p>Wrap in a Celery task. Input: s3\_key (APK path).</p><p>Output: publish StaticReport JSON to Kafka "risk.scores".</p><p>Add Redis as Celery broker.</p><p>On completion, set a "static\_done" flag in Redis with the APK sha256 as key.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 3.2 — AI CLI Agent (aegis scan)**
This runs in parallel with Prompt 3.1 on the same APK. The CLI agent uses Claude to reason about decompiled code and spot threats that pure static rules cannot detect.

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build a CLI tool named "aegis" using Python + Click + Rich + Anthropic SDK.</p><p></p><p>Commands:</p><p>`  `aegis scan <apk\_path></p><p>`    `- Download APK from MinIO using s3\_key</p><p>`    `- Decompile with apktool + jadx (reuse output dir if static engine is running)</p><p>`    `- Send decompiled code to Claude API for AI security analysis:</p><p>`        `\* Detect business-logic abuse</p><p>`        `\* Detect hidden data collection patterns</p><p>`        `\* Detect command-and-control callback patterns</p><p>`        `\* Detect anti-analysis / anti-debug techniques</p><p>`    `- Display findings in a Rich table with color-coded severity</p><p>`    `- Produce risk score 0-100</p><p>`    `- Set "ai\_done" flag in Redis with APK sha256 as key</p><p></p><p>`  `aegis report --input <scan\_json> --format [pdf|json|html]</p><p>`    `- Generate professional report from scan output</p><p></p><p>`  `aegis device <device\_id> --api-key <key></p><p>`    `- Query AEGIS backend for device risk posture</p><p></p><p>`  `aegis config set --api-url <url> --api-key <key></p><p>`    `- Store config in ~/.aegis/config.yaml</p><p></p><p>Merger process (separate worker):</p><p>`  `- Poll Redis for both "static\_done" AND "ai\_done" flags for the same sha256</p><p>`  `- When both are set, merge StaticReport + AI findings into a FinalReport</p><p>`  `- Publish FinalReport to Kafka "risk.scores"</p><p></p><p>Use claude-sonnet-4-20250514. Temperature 0.2 (factual output).</p><p>Include pyproject.toml. Add README with install and usage instructions.</p>|
| :- |

|<p>**🔐  Security Note**</p><p>The AI agent must be given only the decompiled code — never the raw APK binary. Keep prompts focused: send one class/module at a time if the codebase is large, not the entire decompiled output in one call.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

|**PH 04**|<p>**Log Streaming — AI Agent on Important Logs Only**</p><p>⏱ Weeks 13–15</p>|
| :-: | :- |

Important logs are already filtered on-device (Phase 1). Here they are streamed from the server via Kafka and analyzed by an AI agent. No routine logs are ever stored or processed.

## **Prompt 4.1 — Log Stream Processor**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build a Python log stream processor that consumes the Kafka "logs.stream" topic.</p><p></p><p>LogStreamProcessor:</p><p>1\. Consume ImportantLog messages from logs.stream in real-time</p><p>2\. Apply a second-pass filter (logs already filtered on-device, but verify):</p><p>`   `- Confirm message matches threat keyword list</p><p>`   `- Skip any log that is a duplicate of a log seen for the same device in the</p><p>`     `last 60 seconds (use Redis for dedup with 60s TTL key: device\_id:log\_hash)</p><p>3\. Group logs by device\_id in a 5-second tumbling window</p><p>4\. After each window, if any logs remain → forward the batch to the AI Log Analyst</p><p>5\. Track stats: total received, passed filter, sent to AI (expose on /metrics)</p><p></p><p>The processor must be stateless and horizontally scalable (Kafka consumer groups).</p><p>Add Docker deployment configuration.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 4.2 — AI Log Analyst Agent**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build a Python AI Log Analyst that receives batches of important logs per device.</p><p></p><p>AILogAnalyst:</p><p>1\. Receive a batch: {device\_id, logs: [ImportantLog], device\_risk\_context: RiskScore}</p><p>2\. Build a structured prompt for Claude API:</p><p>`   `- Include current device risk score as context</p><p>`   `- Include the log batch</p><p>`   `- Ask Claude to detect:</p><p>`     `\* Privilege escalation attempts</p><p>`     `\* Repeated authentication failures (brute force patterns)</p><p>`     `\* Unusual process spawning</p><p>`     `\* Data exfiltration indicators (large outbound bursts)</p><p>`     `\* Permission abuse patterns</p><p>`     `\* Crash loops that may indicate exploit attempts</p><p>3\. Parse Claude response into a LogThreatReport:</p><p>`   `threat\_type, severity (LOW/MED/HIGH/CRITICAL), confidence, description, raw\_evidence</p><p>4\. Publish LogThreatReport to Kafka "risk.scores"</p><p></p><p>Use claude-sonnet-4-20250514. Temperature 0.2.</p><p>Rate limit: 100 Claude calls / hour (Redis counter with 1h TTL).</p><p>Store all prompts + responses in PostgreSQL for audit trail.</p><p>Add pytest tests with mocked Claude responses.</p>|
| :- |

|<p>**🔐  Security Note**</p><p>The AI agent only sees pre-filtered important logs — never raw device logcat. This protects privacy and keeps AI costs low. The dedup step in the stream processor prevents the same event from triggering multiple AI calls.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

|**PH 05**|<p>**Risk Engine, SOC Dashboard & Response Automation**</p><p>⏱ Weeks 16–20</p>|
| :-: | :- |

Aggregate all signals into composite risk scores, expose them through a real-time SOC dashboard, and automatically enforce MDM responses when thresholds are crossed.

## **Prompt 5.1 — Risk Scoring Engine**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build the AEGIS Risk Engine in Python. It consumes the Kafka "risk.scores" topic</p><p>and computes a composite RiskScore per device and per app.</p><p></p><p>Formula:</p><p>`  `RiskScore = (0.35 \* StaticAnalysis) + (0.35 \* DevicePosture)</p><p>`            `+ (0.20 \* LogThreats) + (0.10 \* ThreatIntel)</p><p></p><p>DevicePosture sub-scoring:</p><p>`  `+40 pts  if is\_rooted == True</p><p>`  `+30 pts  if play\_integrity == FAILS</p><p>`  `+20 pts  if security\_patch is older than 90 days</p><p>`  `+10 pts  if bootloader == unlocked</p><p></p><p>StaticAnalysis sub-scoring (from FinalReport):</p><p>`  `+25 pts  if secrets found</p><p>`  `+20 pts  if obfuscation detected</p><p>`  `+per-permission risk from permission\_risk\_matrix.json</p><p>`  `+15 pts  if known tracker SDKs detected</p><p>`  `+ AI findings severity score (from CLI agent)</p><p></p><p>LogThreats: AILogAnalyst severity → mapped to 0–40 pts</p><p></p><p>ThreatIntel: async VirusTotal hash lookup</p><p>`  `+50 pts  if VT detections > 3</p><p></p><p>Output: RiskScore(device\_id, app\_id, score, severity, breakdown, timestamp)</p><p>Persist to PostgreSQL.</p><p>Publish to Kafka "response.actions" if score >= 75.</p><p>Alert deduplication: same device+app pair silent for 4 hours unless score</p><p>increases by >= 10 points.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 5.2 — SOC Dashboard (API + Frontend)**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build the AEGIS SOC Dashboard.</p><p></p><p>FastAPI Backend:</p><p>`  `GET  /api/v1/devices             — paginated device fleet list with risk scores</p><p>`  `GET  /api/v1/devices/{id}        — device detail: posture, apps, alert history, logs</p><p>`  `GET  /api/v1/devices/{id}/apps   — apps installed on device with risk scores</p><p>`  `GET  /api/v1/alerts              — alert feed (filterable by severity/date)</p><p>`  `GET  /api/v1/alerts/{id}         — alert detail with full risk breakdown</p><p>`  `POST /api/v1/response/{alert\_id} — trigger response action</p><p>`  `WS   /ws/alerts                  — WebSocket real-time alert stream</p><p></p><p>Auth: JWT Bearer tokens (HS256). GET /auth/login endpoint.</p><p>Roles: ANALYST (read only), RESPONDER (can trigger actions), ADMIN.</p><p>PostgreSQL with SQLAlchemy 2.0 async. Alembic for migrations.</p><p></p><p>React Frontend (Vite + TypeScript + TailwindCSS dark theme):</p><p>`  `/dashboard   — KPI cards (safe/at-risk/critical) + risk histogram + live ticker</p><p>`  `/devices     — Sortable/filterable fleet table with risk badges</p><p>`  `/devices/:id — Posture card + installed apps + alert timeline + log viewer</p><p>`                 `+ Action buttons: Quarantine / Flag for Review</p><p>`  `/alerts      — Severity filter tabs: All / Critical / High / Medium</p><p></p><p>Color system: red=critical, orange=high, yellow=medium, green=safe.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

## **Prompt 5.3 — MDM Response Engine**

|<p>**📋  COPY & PASTE TO CLAUDE**</p><p>Build the AEGIS Response Engine. It consumes the Kafka "response.actions" topic.</p><p></p><p>Action types (enum):</p><p>`  `ALERT\_SOC        — send alert to SOC dashboard WebSocket (always executed)</p><p>`  `RESTRICT\_NETWORK — push Intune compliance policy to restrict network access</p><p>`  `QUARANTINE       — mark device non-compliant in Intune via Graph API</p><p>`  `CREATE\_TICKET    — auto-create Jira incident ticket with risk breakdown</p><p>`  `NOTIFY\_USER      — push FCM notification to device</p><p></p><p>Severity routing:</p><p>`  `MEDIUM   → ALERT\_SOC + CREATE\_TICKET</p><p>`  `HIGH     → above + NOTIFY\_USER + RESTRICT\_NETWORK</p><p>`  `CRITICAL → all above + QUARANTINE</p><p></p><p>Intune Integration (Microsoft Graph API):</p><p>`  `- Auth via Azure AD app registration (client\_credentials flow)</p><p>`  `- Mark device non-compliant: PATCH /deviceManagement/managedDevices/{id}</p><p></p><p>Jira Integration:</p><p>`  `- Create issue in project AEGIS with severity-mapped priority</p><p>`  `- Include full risk score breakdown in description</p><p></p><p>Log all actions to PostgreSQL with status (success/failed).</p><p>Allow manual retry from SOC dashboard.</p><p>Add dry\_run mode: log what would happen without calling external APIs.</p>|
| :- |

|<p>**🧠  UNDERSTANDING CHECKPOINT**</p><p>Paste this block into Claude after receiving the generated code:</p><p>You are a Staff-Level Software Engineer, Security Engineer, and Technical Educator. Reverse engineer and document the code I will provide. Make me FULLY UNDERSTAND the system as if I built it myself. Produce: Overview · Architecture · Execution Flow · File Breakdown · Key Components · Security Analysis · Weak Points · How to Extend. Now wait for me to provide the codebase.</p>|
| :- |

# **Appendix — Quick Reference**

## **Technology Stack Summary**

|**Layer**|**Technology**|**Why**|
| :- | :- | :- |
|Android Agent|Kotlin + Hilt + WorkManager|Native Android; reliable background jobs; DI|
|Log Filtering|Kotlin + Logcat + Coroutines|On-device filter — only important logs leave device|
|Transport|JSON over HTTPS mTLS|All data from agent → server as structured JSON|
|API Gateway|FastAPI + Python 3.11|Fast async; Pydantic v2 validation; OpenAPI docs|
|Message Bus|Apache Kafka|High-throughput, durable; decouples microservices|
|Static Engine|apktool + jadx + Celery|Industry standard APK tools; async job processing|
|AI Analysis|Claude API (claude-sonnet-4)|Logic threat detection + log anomaly analysis|
|AI CLI|Python + Click + Rich|Human-readable scan output; parallel with static engine|
|Risk Engine|Python + PostgreSQL|Composite scoring; VirusTotal integration|
|Frontend|React + TypeScript + Vite|Fast builds; type safety; WebSocket live alerts|
|Response|Intune + Graph API + Jira|Automated MDM enforcement on high-risk devices|
|Storage|PostgreSQL + MinIO + Redis|Relational for metadata; object for APKs; cache/queue|

## **Prompt Sequence Index**

|**#**|**Phase**|**Prompt**|**Output**|
| :- | :- | :- | :- |
|1\.1|PH1 — Agent|Project Scaffold & Gradle Setup|build files, Hilt DI|
|1\.2|PH1 — Agent|DeviceScanner Module|root, Play Integrity, DeviceReport JSON|
|1\.3|PH1 — Agent|AppIntelligenceCollector|AppSnapshot JSON, delta diffing|
|1\.4|PH1 — Agent|Log Filter Agent|ImportantLogs JSON, on-device filter|
|2\.1|PH2 — Ingestion|FastAPI Ingestion Gateway|REST API + Kafka routing|
|2\.2|PH2 — Ingestion|Kafka Topics & Schema Registry|Avro schemas, 6 topics|
|3\.1|PH3 — Analysis|Python Static Analyzer (parallel A)|StaticReport, Celery tasks|
|3\.2|PH3 — Analysis|AI CLI Agent aegis scan (parallel B)|AI findings, merged FinalReport|
|4\.1|PH4 — Logs|Log Stream Processor|Kafka consumer, dedup, windowing|
|4\.2|PH4 — Logs|AI Log Analyst Agent|LogThreatReport, audit trail|
|5\.1|PH5 — Risk|Risk Scoring Engine|RiskScore, VirusTotal, dedup|
|5\.2|PH5 — SOC|SOC Dashboard (API + Frontend)|FastAPI REST+WS, React UI|
|5\.3|PH5 — Response|MDM Response Engine|Intune quarantine, Jira tickets|

## **Architecture Changes from v1**
- Dynamic analysis (Frida / Docker emulator) removed — can be added as Phase 6 if needed later
- All device data now travels as JSON → server first, before any Kafka routing or analysis
- Static Python engine and AI CLI agent run in parallel (same phase, same APK trigger)
- Log analysis uses streaming: only important logs (tagged SECURITY/CRASH/ANOMALY) are processed
- Two-stage log filtering: on-device (Kotlin agent) + dedup pass (stream processor) — AI sees only what matters
- Risk formula updated: LogThreats replaces BehaviorAnomaly from v1 (simpler, no sandbox needed)

AEGIS v2 — 5 Phases · 13 Prompts · ~20 Weeks · Simplified Architecture
Page  of 
