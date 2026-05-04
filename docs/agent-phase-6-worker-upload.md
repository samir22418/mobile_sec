# AEGIS Agent Phase 6 - Worker Upload Wiring

## What Changed

`TelemetrySyncWorker` now uploads telemetry after a successful scan is persisted.

The worker still saves the scan before upload. This protects telemetry if the network fails, the backend is down, or the process is killed during upload.

## Runtime Flow

```text
TelemetrySyncWorker.doWork()
  -> mark RUNNING
  -> collect device telemetry
  -> collect app inventory
  -> mark SUCCESS
  -> scan becomes upload_status=PENDING
  -> UploadTelemetryUseCase drains pending/failed uploads
  -> mark UPLOADED or FAILED
```

## Retry Behavior

For this POC phase:

- scan failure returns `Result.retry()`
- upload use case failure returns `Result.retry()`
- partial upload failure returns `Result.retry()`
- successful upload drain returns `Result.success()`

Failed payloads remain in the Room upload queue with retry metadata.

This is intentionally simple. A later production tuning phase can decide whether upload failures should always retry the worker immediately or wait for the next periodic scan to conserve battery.

## Files Updated

`TelemetrySyncWorker.kt`

- Injects `UploadTelemetryUseCase`.
- Calls upload after `markSuccess`.
- Logs upload summary.
- Retries work when upload failures remain queued.

`UploadTelemetryUseCase.kt`

- `UploadTelemetrySummary` now exposes `hasFailures`.

## What Still Needs Work

- The sample app still points to `https://api.aegis.internal`.
- A local POC server is needed for end-to-end upload testing.
- Emulator/device testing should use a reachable `backendUrl`, such as `http://10.0.2.2:<port>` for Android emulator.
- Log batches are still not included in payloads.

## Verification

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```
