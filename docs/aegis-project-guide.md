# AEGIS Project Guide

This guide explains the current AEGIS Android project: what each module does,
how a scan starts, how scan data moves through the system, and where data is
stored.

## 1. What this project is

AEGIS is an Android security agent prototype. It is built as a reusable Android
library plus a sample app.

The library module is:

`aegis-agent/`

The sample host app is:

`app/`

The sample app demonstrates how a real Android application would embed the AEGIS
library, initialize it, trigger scans, and display saved results.

## 2. Module structure

### Root Gradle project

Important files:

- `settings.gradle.kts`
- `build.gradle.kts`
- `gradle/libs.versions.toml`

Purpose:

These files define the Gradle project, modules, plugins, and dependency
versions.

Current modules:

- `:aegis-agent` - reusable security agent library
- `:app` - sample Android app that hosts the library

### Library module

Path:

`aegis-agent/src/main/java/com/aegis/agent/`

Main responsibilities:

- Public SDK entry point
- Device security scanning
- App inventory scanning
- Log filtering
- Background worker orchestration
- Dependency injection
- Saved scan result persistence

### Sample app module

Path:

`app/src/main/java/com/aegis/agent/sample/`

Main responsibilities:

- Creates the Android Application class
- Calls `AegisSdk.init(...)`
- Provides a dashboard UI
- Lets the user request a manual scan
- Observes the latest saved scan record

## 3. Important library files

### `AegisSdk.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/AegisSdk.kt`

Purpose:

This is the public API for host apps.

Important functions:

- `init(context, config)` stores runtime config and schedules periodic scans.
- `requestScanNow(context)` queues an immediate manual scan.
- `shutdown(context)` cancels scheduled scan work.

### `AgentConfig.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/domain/model/AgentConfig.kt`

Purpose:

Defines runtime configuration passed by the host app.

Important fields:

- `backendUrl`
- `deviceId`
- `enrollmentToken`
- `isByodMode`
- `scanIntervalMin`
- `cloudProjectNumber`

### `TelemetrySyncWorker.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/worker/TelemetrySyncWorker.kt`

Purpose:

This is the scan orchestrator. WorkManager runs it in the background.

It performs this sequence:

1. Create a saved scan record with status `RUNNING`.
2. Run device posture scan.
3. Run app inventory scan.
4. Save final result as `SUCCESS`.
5. Save `FAILED` if any stage fails.

Upload to backend is not implemented yet. The upload placeholder is still in
this worker.

### `DeviceScanner.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/scanner/DeviceScanner.kt`

Purpose:

Collects device posture data.

It collects:

- Root signals
- Play Integrity verdict
- Security patch date
- Bootloader verified boot state

Output model:

`DeviceReport`

### `RootDetector.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/scanner/RootDetector.kt`

Purpose:

Runs local root detection checks.

Checks:

- Known `su` binary paths
- `Build.TAGS` containing `test-keys`
- `/system/app/Superuser.apk`

### `IntegrityApiClient.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/scanner/IntegrityApiClient.kt`

Purpose:

Wraps Google Play Integrity API in a suspending Kotlin API.

Important note:

The Android client receives an encrypted token. The token must be sent to a
trusted backend for final `MEETS_*` or `FAILS` verification. Until backend
verification exists, the app saves `REQUIRES_BACKEND_VERIFICATION` when a token
is received.

Detailed setup guide:

`play-integrity-real-device-guide.md`

### `AppIntelligenceCollector.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/apps/AppIntelligenceCollector.kt`

Purpose:

Scans installed applications and builds app inventory telemetry.

It collects:

- Package name
- Version name
- Version code
- APK SHA-256 hash
- Signing certificate SHA-256 hash
- Requested permissions
- Install source
- System app flag
- First install time
- Last update time

Output model:

`AppSnapshot`

### `PackageEventReceiver.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/apps/PackageEventReceiver.kt`

Purpose:

Listens for install/remove/update package events.

Current status:

It can emit package events as a Flow, but no upload path consumes those events
yet.

### `LogFilterAgent.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/logs/LogFilterAgent.kt`

Purpose:

Reads logcat, filters important security logs, buffers them, and emits batches.

Current status:

The log agent is implemented, but it is not started by `AegisSdk` or the worker
yet. It is ready for a later continuous monitoring stage.

### `ScanResultRepository.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanResultRepository.kt`

Purpose:

Stores scan run history in Room.

It saves:

- Scan status
- Trigger type
- Start time
- Completion time
- Device posture summary
- App inventory summary
- Error message
- Integrity details/error code/token hash
- Full `DeviceReport` JSON
- Full `AppSnapshot` JSON

### `AegisDatabase.kt`

Path:

`aegis-agent/src/main/java/com/aegis/agent/data/persistence/AegisDatabase.kt`

Purpose:

Room database for AEGIS saved records.

Database file on device:

`/data/data/<host-package>/databases/aegis_agent.db`

For the sample app:

`/data/data/com.aegis.agent.sample/databases/aegis_agent.db`

## 4. Important sample app files

### `SampleApp.kt`

Path:

`app/src/main/java/com/aegis/agent/sample/SampleApp.kt`

Purpose:

Initializes AEGIS when the sample app starts.

It calls:

`AegisSdk.init(...)`

This schedules the periodic scan worker.

### `MainActivity.kt`

Path:

`app/src/main/java/com/aegis/agent/sample/ui/MainActivity.kt`

Purpose:

Controls the dashboard UI.

It does three important things:

1. Observes the latest saved scan record.
2. Renders scan status and saved results.
3. Calls `AegisSdk.requestScanNow(...)` when the button is clicked.

### `activity_main.xml`

Path:

`app/src/main/res/layout/activity_main.xml`

Purpose:

Defines the security dashboard UI.

It shows:

- Current scan status
- Last scan time
- Integrity verdict
- Root result
- Total apps
- Changed apps
- Security patch
- Bootloader state
- Saved record id
- Last error

## 5. Scan flow step by step

### App startup flow

1. Android starts the sample app.
2. `SampleApp.onCreate()` runs.
3. `AegisSdk.init(...)` is called.
4. `AgentConfigHolder` stores the runtime config in memory.
5. WorkManager schedules periodic work named `aegis_telemetry_sync`.
6. The sample UI opens and observes saved scan records from Room.

### Manual button flow

1. User taps `Run Security Scan`.
2. `MainActivity` calls `AegisSdk.requestScanNow(applicationContext)`.
3. A one-time WorkManager request named `aegis_manual_scan` is enqueued.
4. WorkManager starts `TelemetrySyncWorker`.
5. Worker saves a Room record with `status = RUNNING`.
6. UI observes the Room update and shows `Scanning`.
7. Worker runs `DeviceScanner`.
8. Worker runs `AppIntelligenceCollector`.
9. Worker saves the completed scan as `SUCCESS`.
10. UI observes the Room update and shows `Complete`.

### Failure flow

1. Worker starts and saves `RUNNING`.
2. A scan stage fails.
3. Worker saves `FAILED` with an error message.
4. WorkManager returns `Result.retry()`.
5. UI shows `Failed` and displays the stored error.

## 6. Where data is stored

### Room database

Used for saved scan records.

File:

`/data/data/<host-package>/databases/aegis_agent.db`

Table:

`scan_records`

Keeps:

- Last 25 scan records
- Summary fields for UI
- Full report JSON for future backend upload/retry
- Integrity details, raw error code, and token hash for debugging

### DataStore

Used for app inventory fingerprints.

File:

`/data/data/<host-package>/files/datastore/aegis_app_inventory.preferences_pb`

Key:

`app_fingerprints_v1`

Purpose:

The app inventory collector uses this to know whether the next app scan is a
full scan or a delta scan.

## 7. How to know a scan is complete

In the UI:

- `Scanning` means the latest scan record is `RUNNING`.
- `Complete` means the latest scan record is `SUCCESS`.
- `Failed` means the latest scan record is `FAILED`.

In Logcat:

- `TelemetrySyncWorker: device scan complete`
- `TelemetrySyncWorker: app inventory complete`

In storage:

Check the latest row in `scan_records`. The `status` column is the source of
truth.

## 8. How to build and test

This machine's default `java` points to a JRE, not a full JDK. Use Android
Studio's bundled JDK:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
```

Run tests:

```powershell
.\gradlew.bat :aegis-agent:testDebugUnitTest --no-daemon
```

Build library:

```powershell
.\gradlew.bat :aegis-agent:assembleDebug --no-daemon
```

Build app:

```powershell
.\gradlew.bat :app:assembleDebug --no-daemon
```

## 9. Current limitations

- Backend upload and Play Integrity token verification are not implemented yet.
- Scan config is still held in memory by `AgentConfigHolder`.
- The log filter agent exists but is not started automatically.
- Room has a migration from version 1 to 2 for the Integrity detail columns.

## 10. Next recommended work

1. Add backend upload and retry queue.
2. Add backend Play Integrity `decodeIntegrityToken` verification.
3. Persist encrypted enrollment config instead of keeping it only in memory.
4. Add a scan details screen that opens full saved JSON.
5. Start and persist important log batches.
