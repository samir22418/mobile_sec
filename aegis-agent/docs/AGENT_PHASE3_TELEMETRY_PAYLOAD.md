# AEGIS Agent Phase 3 - Telemetry Payload Contract

## What Changed

The agent now has an explicit upload payload model and stable payload identity for each successful scan.

This phase does not upload to a server yet. It prepares the agent-side contract that the future uploader and server POC will use.

## Files Added

`TelemetryPayload.kt`

- Combines one scan's `DeviceReport`, `AppSnapshot`, optional `ImportantLog` batch, and enrollment token.
- Uses `@SerialName` snake_case field names for backend compatibility.
- Generates deterministic `payloadId` values from `deviceId`, `scanId`, and scan start time.

`TelemetryPayloadTest.kt`

- Verifies deterministic payload IDs.
- Verifies payload IDs change across scan identities.
- Verifies payload construction from `AgentConfig` and scan data.
- Verifies serialized field names.

## Files Updated

`ScanRecordEntity.kt`

- Adds `payload_id`.
- Adds `payload_created_at_epoch_ms`.

`ScanRecord.kt`

- Exposes payload identity fields to the domain/UI layer.

`AegisDatabase.kt`

- Bumps Room from version 2 to version 3.
- Adds migration 2 -> 3 for payload identity columns.

`PersistenceModule.kt`

- Registers migrations 1 -> 2 and 2 -> 3.

`ScanResultRepository.kt`

- Computes and stores `payloadId` when a scan succeeds.
- Uses the scan record ID plus scan start time so retry code can reuse the same payload identity.

## Token Handling Decision

`TelemetryPayload` includes `enrollmentToken` because the server POC needs a simple enrollment/auth signal.

The full `TelemetryPayload` is not stored in Room because that would duplicate the enrollment token outside encrypted config storage.

Future upload code should rebuild the payload from:

- encrypted `AgentConfig`
- `ScanRecord.payloadId`
- `ScanRecord.id`
- `ScanRecord.startedAtEpochMs`
- `ScanRecord.deviceReportJson`
- `ScanRecord.appSnapshotJson`
- optional log batch

## Current State

Completed scan records now have a stable `payloadId`, but there is still no:

- upload status
- retry count
- last upload error
- upload worker/client
- server call

Those belong to the next phase.

## Verification

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```
