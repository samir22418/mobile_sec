# AEGIS Agent Phase 4 - Upload Queue Persistence

## What Changed

Scan records now carry upload state and retry metadata.

This phase still does not perform network upload. It gives the future uploader a durable queue API.

## Upload State

`UploadStatus`

- `NOT_READY`: scan does not have a complete payload yet, or the scan failed.
- `PENDING`: completed scan is ready to upload.
- `UPLOADING`: an upload attempt is in progress.
- `UPLOADED`: payload was accepted by the server.
- `FAILED`: last upload attempt failed and should be retried later.

## Room Schema

Room is now version 4.

Migration 3 -> 4 adds:

- `upload_status`
- `retry_count`
- `last_upload_attempt_at_epoch_ms`
- `last_upload_error`
- `uploaded_at_epoch_ms`

Successful scans are saved as `PENDING`.

Failed scans are saved as `NOT_READY`.

## Repository API

`ScanResultRepository` now exposes:

- `getPendingUploads(limit)`
- `markUploadAttempt(id)`
- `markUploaded(id)`
- `markUploadFailed(id, error/message)`
- `markUploadPending(id)`

These methods are intended for the next phase's uploader/use case.

## Pruning Rule

Old scan pruning now protects rows with upload status:

- `PENDING`
- `UPLOADING`
- `FAILED`

This prevents unsent payloads from being deleted just because the local history limit is 25 rows.

Uploaded and not-ready rows can still be pruned.

## Next Phase

Build the agent upload client against the POC server:

1. Load encrypted `AgentConfig`.
2. Read upload candidates from `ScanResultRepository`.
3. Rebuild `TelemetryPayload` from config plus saved JSON.
4. POST to POC server.
5. Mark `UPLOADED` or `FAILED`.

## Verification

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```
