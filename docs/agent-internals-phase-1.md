# AEGIS Agent Internals - Phase 1

This note is the agent-first map for working confidently inside the Android SDK before adding upload/retry or a real backend.

## Current Runtime Flow

```text
SampleApp.onCreate()
  -> AegisSdk.init(context, AgentConfig)
  -> AgentConfigHolder.config = config
  -> WorkManager schedules TelemetrySyncWorker

Manual scan button
  -> AegisSdk.requestScanNow()
  -> one-time TelemetrySyncWorker

TelemetrySyncWorker.doWork()
  -> ScanResultRepository.markRunning()
  -> CollectDeviceTelemetryUseCase()
  -> DeviceScanner.scan()
  -> CollectAppInventoryUseCase()
  -> AppIntelligenceCollector.collect()
  -> ScanResultRepository.markSuccess()
  -> MainActivity observes latest scan and renders dashboard
```

## Module Responsibilities

### SDK Entry Point

`AegisSdk.kt`

- Public API for the host application.
- Stores runtime config in `AgentConfigHolder`.
- Schedules periodic scans through WorkManager.
- Provides manual scan and shutdown operations.

- Config is now persisted by `ConfigRepository` and mirrored in memory by `AgentConfigHolder`.
- `ExistingPeriodicWorkPolicy.KEEP` preserves the old schedule if config changes.

### Application / WorkManager Wiring

`AegisApplication.kt`

- Base `Application` class for host apps.
- Provides Hilt's `HiltWorkerFactory` to WorkManager.
- Initializes Timber logging.

Sample host:

- `SampleApp.kt` extends `AegisApplication`.
- `SampleApp` is annotated with `@HiltAndroidApp`.
- It calls `AegisSdk.init()` with placeholder config.

### Worker Orchestration

`TelemetrySyncWorker.kt`

- Orchestrates one scan cycle.
- Creates a `RUNNING` scan row.
- Runs device posture collection.
- Runs app inventory collection.
- Saves a `SUCCESS` or `FAILED` record.

Current limitation:

- Upload is not implemented. The upload placeholder is still present.
- Log collection is not wired into the worker.
- Worker retries scan-stage failures, but there is no upload retry queue yet.

### Device Posture

`DeviceScanner.kt`

- Runs root checks on `Dispatchers.IO`.
- Reads Android security patch date.
- Reads verified boot state through `SystemProperties` reflection.
- Calls Play Integrity on the injected main dispatcher.
- Returns a serializable `DeviceReport`.

`RootDetector.kt`

- Checks common `su` paths.
- Checks `Build.TAGS` for `test-keys`.
- Checks classic `/system/app/Superuser.apk`.

`IntegrityApiClient.kt`

- Wraps Play Integrity in a suspending API.
- Returns `NOT_CONFIGURED` if `cloudProjectNumber <= 0`.
- Returns `REQUIRES_BACKEND_VERIFICATION` when a token is received.
- Stores only token hash, not the raw token.

Important boundary:

- Final `MEETS_*` verdicts require backend token decoding. The Android client cannot safely decode and trust the token locally.

### App Intelligence

`AppIntelligenceCollector.kt`

- Enumerates installed packages.
- Applies BYOD filtering when enabled.
- Computes APK SHA-256 and signing certificate SHA-256 where possible.
- Classifies install source as Play Store, MDM, sideloaded, or unknown.
- Persists package fingerprints in DataStore.
- Emits full inventory on first run and delta inventory on later runs.

`PackageEventReceiver.kt`

- Manifest receiver logs package changes.
- Companion `packageEvents(context)` exposes package changes as a Flow when collected.

Current limitation:

- Package event Flow is not consumed by any upload or scan pipeline yet.
- Removed apps are detected as broadcasts, but the current delta snapshot model only includes `AppInfo` entries for installed/current packages.

### Logs

`LogcatReader.kt`

- Starts `logcat -v brief -b main,crash,system`.
- Parses brief-format lines into `RawLogLine`.

`ImportanceFilter.kt`

- Passes logs by tag keyword, error/assert level, or threat regex.
- Discards everything else immediately.

`LogFilterAgent.kt`

- Starts a reader coroutine and a flush coroutine.
- Buffers matching logs in memory.
- Flushes every 30 seconds or at 50 entries.
- Exposes flushed batches through `filteredLogs`.

Current limitation:

- The agent is provided by Hilt but never started by `AegisSdk` or `TelemetrySyncWorker`.
- Normal third-party Android apps usually cannot read full system logcat. Treat this as best-effort unless running in a privileged/debug/rooted/enterprise context.

### Persistence

`AegisDatabase.kt`

- Room database, currently version 2.
- Migration 1 -> 2 adds Play Integrity detail fields.

`ScanRecordEntity.kt`

- Stores scan status, summary fields, and full device/app JSON payloads.

`ScanRecordDao.kt`

- Inserts and updates scan records.
- Observes latest scan.
- Prunes old records.

`ScanResultRepository.kt`

- Creates running records.
- Marks success/failure.
- Serializes full `DeviceReport` and `AppSnapshot`.
- Keeps only the latest 25 scan records.

Current limitation:

- Upload status exists, but no network uploader consumes it yet.
- Retry count and last upload error are persisted for future uploader use.
- Stable payload identity exists.
- Pruning does not protect future unuploaded records.

### Sample Dashboard

`MainActivity.kt`

- Injects `ScanResultRepository`.
- Observes latest scan record.
- Renders status, posture, integrity details, app count, and last error.
- Queues manual scans.

Current limitation:

- No detail screen for full JSON.
- No upload status display.

## Data Ownership

`AgentConfig`

- Source: host app or MDM provisioning.
- Current storage: encrypted local preferences through `ConfigRepository`.
- Runtime mirror: in-memory `AgentConfigHolder`.

`DeviceReport`

- Source: `DeviceScanner`.
- Stored in Room as compact JSON plus summary columns.
- Future upload: part of `TelemetryPayload`.

`AppSnapshot`

- Source: `AppIntelligenceCollector`.
- Stored in Room as compact JSON plus summary columns.
- Future upload: part of `TelemetryPayload`.

`ImportantLog`

- Source: `LogFilterAgent`.
- Current storage: in-memory buffer only.
- Future upload: optional batch inside `TelemetryPayload`.

`ScanRecord`

- Source: `ScanResultRepository`.
- Purpose: local history and dashboard state.
- Future role: upload queue metadata.

## Sharp Edges To Respect

- Do not trust Play Integrity final verdicts on-device. Send the token to a backend for real verification.
- Do not assume full logcat access on production Android devices.
- Do not use only `uploaded: Boolean` for retries; debugging mobile upload failures needs state and error history.
- Do not prune pending upload records.
- Do not persist raw Play Integrity tokens unless the threat model explicitly accepts it.
- Do not let Hilt singleton providers freeze stale config values before persistent config is loaded.
- Do not let local POC certificate settings leak into production pinning.

## Phase 1 Conclusion

The current agent is a clean local scanner and dashboard with persistent config. It is not yet an EDR-style reporting agent because it lacks upload payload identity, upload status, retry metadata, server communication, and log integration.

The next agent-first implementation step should be running an emulator end-to-end upload/retry test against the POC server.
