# Scan Persistence and Dashboard Additions

This document explains the new work added to save scan results and replace the
sample UI with a usable security dashboard.

## 1. Why saving scan data was added

Before this change, a scan result only lived in memory while
`TelemetrySyncWorker` was running. The worker logged the result, then returned
`Result.success()`. The UI had no reliable way to know:

- whether a scan was running
- whether a scan completed
- whether a scan failed
- what the latest root/integrity/app inventory result was

Saving scan runs fixes that. The UI now observes stored scan state instead of
guessing from logs.

## 2. What was added

### Domain model

File:

`aegis-agent/src/main/java/com/aegis/agent/domain/model/ScanRecord.kt`

Added:

- `ScanStatus`
- `ScanTrigger`
- `ScanRecord`

Purpose:

These models represent a saved scan in a clean, UI-friendly format.

### Room persistence layer

Files:

- `data/persistence/AegisDatabase.kt`
- `data/persistence/ScanRecordEntity.kt`
- `data/persistence/ScanRecordDao.kt`
- `data/persistence/ScanResultRepository.kt`

Purpose:

This layer stores scan records in SQLite through Room.

Database name:

`aegis_agent.db`

Table name:

`scan_records`

Maximum kept records:

25 latest scan records.

### Hilt module

File:

`aegis-agent/src/main/java/com/aegis/agent/di/PersistenceModule.kt`

Purpose:

Provides:

- `AegisDatabase`
- `ScanRecordDao`
- `ScanResultRepository`

This lets both the worker and the sample activity use the same saved scan data.

### Manual scan API

File:

`aegis-agent/src/main/java/com/aegis/agent/AegisSdk.kt`

Added:

`AegisSdk.requestScanNow(context)`

Purpose:

Queues an immediate one-time WorkManager scan. This is what the dashboard button
uses.

### Worker persistence

File:

`aegis-agent/src/main/java/com/aegis/agent/data/worker/TelemetrySyncWorker.kt`

New behavior:

1. Save `RUNNING` when the worker starts.
2. Save `FAILED` if device posture scan fails.
3. Save `FAILED` if app inventory scan fails.
4. Save `SUCCESS` when both scans complete.
5. Store full JSON payloads for future upload/retry work.

### Dashboard UI

Files:

- `app/src/main/java/com/aegis/agent/sample/ui/MainActivity.kt`
- `app/src/main/res/layout/activity_main.xml`
- `app/src/main/res/values/themes.xml`

New behavior:

- Button triggers a real manual scan.
- UI observes `ScanResultRepository.observeLatest()`.
- UI updates automatically when Room records change.
- UI shows status, summary metrics, saved record id, Integrity details, and last error.

## 3. Saved fields

Each saved scan record stores:

- `id`
- `status`
- `trigger`
- `started_at_epoch_ms`
- `completed_at_epoch_ms`
- `device_id`
- `is_rooted`
- `integrity_verdict`
- `integrity_details`
- `integrity_error_code`
- `integrity_token_hash_sha256`
- `security_patch_date`
- `bootloader_state`
- `total_app_count`
- `changed_app_count`
- `is_app_delta`
- `error_message`
- `device_report_json`
- `app_snapshot_json`

## 4. Why Room was chosen

DataStore is still used for small app inventory fingerprint state. That is the
right storage for a single key/value-style fingerprint set.

Room was added for scan records because scan history is structured data. It has
fields, rows, status transitions, and future upload/retry requirements.

Simple rule:

- DataStore: small state and settings
- Room: scan records and history

## 5. What happens after tapping Run Security Scan

1. `MainActivity` receives the click.
2. It calls `AegisSdk.requestScanNow(applicationContext)`.
3. WorkManager enqueues `aegis_manual_scan`.
4. `TelemetrySyncWorker` starts.
5. Worker inserts a Room row with `RUNNING`.
6. UI observes that row and shows `Scanning`.
7. Worker runs `DeviceScanner`.
8. Worker runs `AppIntelligenceCollector`.
9. Worker updates the row to `SUCCESS` with summary and JSON data.
10. UI observes the update and shows `Complete`.

If anything fails:

1. Worker updates the row to `FAILED`.
2. Worker stores the error message.
3. UI shows `Failed`.

## 6. How to inspect saved data on a device

The database path for the sample app is:

`/data/data/com.aegis.agent.sample/databases/aegis_agent.db`

The table is:

`scan_records`

Useful adb command on a debuggable emulator/device:

```bash
adb shell run-as com.aegis.agent.sample ls databases
```

To copy the database:

```bash
adb exec-out run-as com.aegis.agent.sample cat databases/aegis_agent.db > aegis_agent.db
```

## 7. Important design notes

The latest scan record is the UI source of truth.

The worker is the only component that changes scan state from `RUNNING` to
`SUCCESS` or `FAILED`.

The full JSON payloads are saved because the backend upload layer is not built
yet. When upload is added, it can read these records and retry failed uploads.

## 8. Future improvements

Recommended next work:

- Add an `upload_status` column.
- Add a backend upload worker.
- Encrypt saved report JSON if sensitive data is included.
- Add a scan details screen.
- Continue adding explicit Room migrations for every future schema change.
