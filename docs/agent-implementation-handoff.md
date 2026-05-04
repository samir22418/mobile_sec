# AEGIS Agent Implementation Handoff

This document summarizes the agent-first work completed so far, how the current system behaves, how to verify it, and what phases should come next.

## Current Goal

The Android agent is the primary focus. The backend is intentionally only a POC receiver so another teammate can own the production server later.

The current target is:

- collect device posture
- collect app inventory
- persist scans locally
- persist agent config across process death/reboot
- build stable telemetry payloads
- queue uploads durably
- POST telemetry to a tiny POC server
- retry failed uploads through WorkManager
- prove upload success/failure/recovery on an Android emulator
- provide a stronger sample-app analyst console for demos and handoff

## Baseline Environment

Gradle must run with a full JDK. On this machine, the default shell Java points to a JRE:

```text
C:\Program Files\Eclipse Adoptium\jre-17.0.8.101-hotspot
```

Use Android Studio's bundled JDK:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
```

Baseline commands:

```powershell
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```

Both commands should pass.

## Implemented Phases

### Phase 0 - Baseline

Validated that the project builds and tests when Gradle uses a full JDK.

Added:

- `agent-baseline-and-flow.md`

Main discovery:

- The original build failure was environmental, not a code failure.
- The default Java install lacked `javac`.

### Phase 1 - Agent Internals Study

Mapped the existing agent lifecycle and module responsibilities.

Added:

- `agent-internals-phase-1.md`

Confirmed architecture:

```text
AegisSdk.init()
  -> WorkManager schedules TelemetrySyncWorker
  -> TelemetrySyncWorker marks RUNNING
  -> CollectDeviceTelemetryUseCase
  -> DeviceScanner
  -> CollectAppInventoryUseCase
  -> AppIntelligenceCollector
  -> ScanResultRepository marks SUCCESS/FAILED
  -> MainActivity observes latest record
```

Key existing modules:

- `AegisSdk.kt`: public SDK entry point
- `TelemetrySyncWorker.kt`: scan/upload orchestration
- `DeviceScanner.kt`: root, Play Integrity, patch date, bootloader state
- `AppIntelligenceCollector.kt`: package inventory and delta fingerprints
- `LogFilterAgent.kt`: worker-scoped important-log capture
- `ScanResultRepository.kt`: Room-backed scan state

### Phase 2 - Config Persistence

Added encrypted config persistence so the agent can survive process death and reboot.

Added:

- `ConfigRepository.kt`
- `AgentConfigHolderTest.kt`
- `agent-phase-2-config-persistence.md`

Updated:

- `AegisSdk.kt`
- `BootReceiver.kt`
- `ScannerModule.kt`
- `AppModule.kt`
- `libs.versions.toml`
- `aegis-agent/build.gradle.kts`

Behavior now:

1. Host app calls `AegisSdk.init(context, config)`.
2. `ConfigRepository` saves `AgentConfig` in encrypted preferences.
3. `AgentConfigHolder` mirrors config in memory.
4. Hilt providers read memory first, then encrypted storage.
5. `BootReceiver` can restore the schedule from persisted config.
6. `AegisSdk.shutdown()` cancels work and clears persisted config.

Security note:

- `AgentConfig.enrollmentToken` is stored encrypted.
- AndroidX Security Crypto is used for this POC.
- A production hardening phase can replace the internals with direct Android Keystore usage while keeping the same repository boundary.

### Phase 3 - Telemetry Payload Contract

Added the upload contract and stable payload identity.

Added:

- `TelemetryPayload.kt`
- `TelemetryPayloadTest.kt`
- `agent-phase-3-telemetry-payload.md`

Updated:

- `ScanRecordEntity.kt`
- `ScanRecord.kt`
- `AegisDatabase.kt`
- `PersistenceModule.kt`
- `ScanResultRepository.kt`

Room migration:

- version 2 -> 3
- adds `payload_id`
- adds `payload_created_at_epoch_ms`

Payload identity:

```text
payloadId = UUID.nameUUIDFromBytes("aegis:<deviceId>:<scanId>:<startedAtEpochMs>")
```

Important token decision:

- `TelemetryPayload` includes `enrollmentToken`.
- The full payload is not stored in Room.
- Future upload code rebuilds payloads from encrypted config plus saved scan JSON.

### Phase 4 - Upload Queue Persistence

Added durable upload state and retry metadata.

Added:

- `UploadStatus` enum
- `ScanRecordTest.kt`
- `agent-phase-4-upload-queue.md`

Updated:

- `ScanRecordEntity.kt`
- `ScanRecordDao.kt`
- `ScanResultRepository.kt`
- `AegisDatabase.kt`
- `PersistenceModule.kt`

Room migration:

- version 3 -> 4
- adds `upload_status`
- adds `retry_count`
- adds `last_upload_attempt_at_epoch_ms`
- adds `last_upload_error`
- adds `uploaded_at_epoch_ms`

Upload states:

```text
NOT_READY  -> scan is incomplete or failed
PENDING    -> completed scan is ready to upload
UPLOADING  -> upload attempt in progress
UPLOADED   -> accepted by server
FAILED     -> upload failed and should retry
```

Repository upload API:

- `getPendingUploads(limit)`
- `markUploadAttempt(id)`
- `markUploaded(id)`
- `markUploadFailed(id, error/message)`
- `markUploadPending(id)`

Pruning behavior:

- local scan history still keeps recent rows
- rows in `PENDING`, `UPLOADING`, or `FAILED` are protected from pruning
- uploaded/not-ready rows can be pruned

### Phase 5 - Upload Client

Added the HTTP uploader and upload use case.

Added:

- `TelemetryUploader.kt`
- `UploadTelemetryUseCase.kt`
- `TelemetryUploaderTest.kt`
- `UploadTelemetryUseCaseTest.kt`
- `agent-phase-5-upload-client.md`

Updated:

- `NetworkModule.kt`
- `libs.versions.toml`
- `aegis-agent/build.gradle.kts`

Uploader behavior:

- POSTs JSON to `{backendUrl}/api/v1/telemetry`
- sends headers:
  - `X-Aegis-Payload-Id`
  - `X-Aegis-Device-Id`
- treats any 2xx response as success
- wraps non-2xx responses in `TelemetryUploadException`

Use case behavior:

1. loads encrypted `AgentConfig`
2. fetches pending/failed scans
3. marks each upload attempt
4. rebuilds `TelemetryPayload`
5. calls `TelemetryUploader`
6. marks uploaded or failed
7. returns `UploadTelemetrySummary`

Network note:

- certificate pinning is only applied when real pins are configured
- placeholder pins no longer break local POC testing

### Phase 6 - Worker Upload Wiring

Connected the upload use case to the worker.

Added:

- `agent-phase-6-worker-upload.md`

Updated:

- `TelemetrySyncWorker.kt`
- `UploadTelemetryUseCase.kt`

Current worker flow:

```text
TelemetrySyncWorker.doWork()
  -> mark RUNNING
  -> collect device report
  -> collect app snapshot
  -> mark SUCCESS
  -> scan becomes PENDING
  -> UploadTelemetryUseCase drains pending/failed records
  -> mark UPLOADED or FAILED
```

POC retry behavior:

- scan failure -> `Result.retry()`
- upload use case failure -> `Result.retry()`
- partial upload failure -> `Result.retry()`
- full upload success -> `Result.success()`

This is intentionally simple. Production can tune whether upload failures should immediately retry or wait for the next periodic scan.

### Phase 7 - POC Server

Added a tiny local telemetry receiver for agent upload/retry testing.

Added:

- `poc-server/aegis_poc_server.py`
- `agent-phase-7-poc-server.md`

### Phase 8 - Emulator End-To-End Upload And Retry Test

Validated the complete agent-side loop on an Android emulator.

Added:

- `agent-phase-8-e2e-test-results.md`

Verified:

- emulator reaches host POC server through `http://10.0.2.2:8080`
- successful scan uploads to `POST /api/v1/telemetry`
- forced HTTP 500 leaves the scan queued and returns WorkManager `RETRY`
- recovery run uploads the previously failed payload first
- server JSONL line count moved `1 -> 1 -> 3` across success, forced failure, and recovery

Observed payload IDs:

```text
success:   c9c9ebeb-23db-311a-bd25-9b74887d3e14
failed:    ecabcbfa-20d7-31da-b6d3-cc54402ac665
recovery:  a9e02e91-915d-3752-ae09-d88262adf206
```

### Phase 9 - Scan Detail And Upload Debug UI

Added a sample-app debug view so scan/upload evidence can be inspected without Room or logcat.

Added:

- `ScanDetailActivity.kt`
- `activity_scan_detail.xml`
- `agent-phase-9-scan-detail-ui.md`

Updated:

- `MainActivity.kt`
- `activity_main.xml`
- `AndroidManifest.xml`
- `ScanRecordDao.kt`
- `ScanResultRepository.kt`
- `app/build.gradle.kts`

Behavior now:

- dashboard shows latest payload ID, upload status, retry count, last attempt, uploaded-at time, and last upload error
- dashboard can open the latest scan detail
- detail screen observes the chosen scan by ID
- detail screen shows scan metadata, upload metadata, device JSON, and app snapshot JSON
- copy actions export upload summary, device JSON, and app JSON

### Phase 10 - Log Agent Integration

Integrated important-log capture into the worker scan/upload flow.

Added:

- `agent-phase-10-log-integration.md`

Updated:

- `LogFilterAgent.kt`
- `TelemetrySyncWorker.kt`
- `ScanResultRepository.kt`
- `ScanRecordEntity.kt`
- `ScanRecord.kt`
- `UploadTelemetryUseCase.kt`
- `AegisDatabase.kt`
- `PersistenceModule.kt`
- sample app dashboard/detail UI

Behavior now:

- worker captures a short important-log snapshot during scan
- scan records persist `important_log_count` and `important_logs_json`
- Room migration `4 -> 5` preserves existing records
- retry payload rebuild includes the same persisted important logs
- sample app displays and copies logs JSON

### Phase 11 - Backend Handoff Essentials

Pulled forward the production-handoff pieces needed by the server, AI, and data-processing owner.

Added:

- `backend-data-engineering-handoff.md`
- `agent-phase-11-backend-handoff.md`
- `poc-server/telemetry_schema_v1.json`

Defined:

- endpoint contract
- payload schema
- idempotency key: `payload_id`
- retry expectations
- suggested storage model
- suggested processing pipeline
- initial AI/model feature ideas
- production auth/mTLS/pinning notes

### Final UI Enhancement

Added a stronger sample-app analyst console pass.

Added:

- `agent-final-ui-enhancement.md`
- `RiskBrief.kt`

Behavior now:

- dashboard shows a local risk score, label, headline, and reasons
- dashboard shows recent scans and lets the user open any recent scan detail
- detail screen shows a copyable analyst brief
- repository exposes read-only recent scan observation

This is still local explainable demo scoring; backend AI/model scoring remains the responsibility of the server/data pipeline.

### UI Theme Enhancement

Added dark/light mode support and moved sample-app colors into resource palettes.

Added:

- `ui-theme-enhancement.md`
- `values/colors.xml`
- `values-night/colors.xml`

Behavior now:

- dashboard has a `Dark Mode` / `Light Mode` toggle
- selected theme mode is saved locally
- dashboard and detail layouts use semantic theme colors
- recent scan rows and status surfaces adapt to the active mode

### UI/UX Mini-Scope Completion

Implemented the requested low-complexity scanner UX improvements.

Added:

- `ui-ux-mini-scope-completion.md`
- `SettingsActivity.kt`
- `activity_settings.xml`

Behavior now:

- dashboard includes upload/root/integrity chips
- dashboard shows recommended action text
- recent scans support All, Failed, Uploaded, and Review filters
- dashboard can share the latest analyst brief as text
- detail screen can share the analyst brief as text
- raw JSON sections are hidden by default and can be expanded on demand
- minimal read-only settings screen shows backend URL, device ID, enrollment status, latest payload, and latest upload state

### Project Cleanup And Validation

Removed generated/runtime folders and revalidated the project.

Added:

- `project-cleanup-and-validation.md`

Removed locally:

- `build`
- `.gradle`
- `app/build`
- `aegis-agent/build`
- `poc-server-data`

Validation:

- agent unit tests passed
- app debug build passed
- POC server smoke passed
- emulator UI smoke passed

Updated:

- `app/build.gradle.kts`
- `SampleApp.kt`
- `app/src/main/AndroidManifest.xml`

Server endpoints:

```text
GET  /health
POST /api/v1/telemetry
GET  /fail?enabled=true
GET  /fail?enabled=false
```

Accepted telemetry is appended to:

```text
poc-server-data/telemetry.jsonl
```

The sample app now reads:

```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
```

from `local.properties` or Gradle properties.

The sample app allows cleartext HTTP for POC testing. This change is isolated to the sample app, not the library module.

POC server smoke test passed:

- `/health` returns OK
- telemetry POST returns accepted
- forced failure returns HTTP 500
- JSONL contains the submitted payload

## Current End-To-End Architecture

```text
SampleApp
  -> AegisSdk.init(config)
  -> ConfigRepository saves encrypted config
  -> WorkManager runs TelemetrySyncWorker
  -> DeviceScanner builds DeviceReport
  -> AppIntelligenceCollector builds AppSnapshot
  -> ScanResultRepository saves scan and marks PENDING
  -> UploadTelemetryUseCase rebuilds TelemetryPayload
  -> TelemetryUploader POSTs to POC server
  -> ScanResultRepository marks UPLOADED or FAILED
  -> MainActivity observes latest scan summary
```

## Current Verification Commands

Run from repo root:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```

Run POC server:

```powershell
python .\poc-server\aegis_poc_server.py --host 0.0.0.0 --port 8080
```

Configure emulator backend:

```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
```

Force upload failure:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=true
```

Disable forced failure:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=false
```

## Known Limitations

### Backend

The POC server is not production:

- no auth
- no mTLS
- no database
- no Kafka
- no schema validation beyond basic field presence
- no SOC/risk dashboard

This is intentional because another teammate owns the production backend.

### Play Integrity

The Android app receives an encrypted Play Integrity token. The final `MEETS_*` verdict must be decoded by a trusted backend.

The agent currently stores token hash only, not the raw token.

### Log Agent

`LogFilterAgent` is integrated as a worker-scoped best-effort capture window and persisted in `important_logs_json`.

On normal production Android devices, full system logcat access is limited. Treat log collection as best-effort unless running with a privileged/debug/rooted/enterprise context.

### Sample UI

The dashboard and detail screen are debug/demo tools, not a production SOC dashboard.

They now show:

- full JSON payloads
- upload status
- retry count
- last upload error
- payload ID
- important logs JSON

### Certificate Pinning

The network module has placeholder pin constants. Pinning is disabled until real pins are configured.

Production should add real SHA-256 pins for the production host.

## Next Phases

### Phase 12 - Test Matrix

Goal:

Turn the agent into something repeatably demoable and regression-safe.

Tasks:

- JVM tests for repository/use-case edge cases
- instrumentation test for config persistence if emulator is available
- emulator test for upload success/failure
- migration tests for Room versions 1 -> 5
- manual test checklist for root/integrity/app inventory/upload/logs

Deliverable:

- `agent-test-matrix.md`
- repeatable test commands

### Phase 13 - Production Hardening Completion

Goal:

Finish the remaining production security work after backend ownership is active.

Tasks:

- replace POC token style in the agent after backend auth is chosen
- implement mTLS/client certificate enrollment if selected
- replace placeholder cert pins with real pins
- wire backend Play Integrity challenge/decode flow
- tune WorkManager retry/battery/network constraints
- consider direct Android Keystore replacement for config encryption

Deliverable:

- production security checklist
- final backend integration checklist

## Recommended Immediate Next Step

Hand off the server/data/AI work next.

The complete agent-side POC loop is now proven:

```text
Android sample app -> WorkManager -> Room queue -> uploader -> POC server -> JSONL
```

The Android agent-side POC contract is ready. The data engineer can build production ingestion, storage, feature extraction, AI/risk scoring, and data processing from `backend-data-engineering-handoff.md` and `poc-server/telemetry_schema_v1.json`.
