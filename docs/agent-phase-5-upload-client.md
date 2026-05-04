# AEGIS Agent Phase 5 - Upload Client

## What Changed

The agent now has a client-side upload path that can send pending scan payloads to a POC backend.

This phase does not wire upload into `TelemetrySyncWorker` yet. It provides the reusable uploader and use case that the worker will call in the next phase.

## POC Server Contract

The POC server should expose:

```text
POST /api/v1/telemetry
Content-Type: application/json
Accept: application/json
X-Aegis-Payload-Id: <payload_id>
X-Aegis-Device-Id: <device_id>
```

Expected behavior:

- Return any 2xx response for accepted payloads.
- Return non-2xx to trigger retry handling.
- The request body is serialized `TelemetryPayload`.
- The backend should treat `payload_id` as idempotent.

## Files Added

`TelemetryUploader.kt`

- Builds the endpoint URL from `AgentConfig.backendUrl`.
- POSTs `TelemetryPayload` JSON to `/api/v1/telemetry`.
- Sends payload/device IDs as headers.
- Returns `Result<Unit>`.
- Wraps non-2xx responses in `TelemetryUploadException`.

`UploadTelemetryUseCase.kt`

- Loads encrypted `AgentConfig`.
- Reads pending/failed upload candidates.
- Rebuilds `TelemetryPayload` from stored scan JSON plus enrollment token.
- Marks upload attempt, success, or failure in `ScanResultRepository`.
- Returns `UploadTelemetrySummary`.

## Files Updated

`NetworkModule.kt`

- Certificate pinning is now applied only when real pins are configured.
- Placeholder pins no longer break POC/local clients.
- Production should replace the placeholder constants with real base64 SHA-256 pins.

`libs.versions.toml` and `aegis-agent/build.gradle.kts`

- Adds `okhttp-mockwebserver` for unit tests.

## Tests Added

`TelemetryUploaderTest.kt`

- Verifies POST path, headers, and JSON body against MockWebServer.
- Verifies non-2xx responses return `TelemetryUploadException`.

`UploadTelemetryUseCaseTest.kt`

- Verifies scan records are rebuilt into `TelemetryPayload`.
- Verifies missing JSON fails before upload.

## Next Phase

Wire `UploadTelemetryUseCase` into `TelemetrySyncWorker`:

1. After a scan is saved successfully, call upload use case.
2. Upload all pending/failed candidates.
3. Return `Result.retry()` when upload fails, or keep scan success and allow later retry.
4. Keep this behavior simple for POC, then tune battery/network behavior later.

## Verification

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```
