# AEGIS Agent Phase 9 - Scan Detail And Upload Debug UI

## Purpose

Phase 9 makes the sample app useful for demos and manual debugging without requiring Room inspection or logcat for every scan.

The screen is still a sample/debug surface. It is not the production SOC dashboard.

## What Changed

### Dashboard

Updated:

```text
app/src/main/java/com/aegis/agent/sample/ui/MainActivity.kt
app/src/main/res/layout/activity_main.xml
```

The main screen now shows upload metadata for the latest scan:

- payload ID
- upload status
- retry count
- last upload attempt
- uploaded-at time
- last upload error

It also includes an `Open Scan Detail` action. The button is disabled until at least one scan record exists.

### Detail Screen

Added:

```text
app/src/main/java/com/aegis/agent/sample/ui/ScanDetailActivity.kt
app/src/main/res/layout/activity_scan_detail.xml
```

The detail screen shows:

- scan ID, status, and trigger
- payload ID
- upload status
- retry count
- last upload attempt
- uploaded-at time
- last upload error
- started/completed timestamps
- device ID
- root status
- integrity verdict
- security patch
- bootloader state
- app counts
- scan error
- full device report JSON
- full app snapshot JSON

Copy actions:

- copy upload summary
- copy device report JSON
- copy app snapshot JSON

### Repository Read API

Updated:

```text
aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanRecordDao.kt
aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanResultRepository.kt
```

Added:

```kotlin
fun observeById(id: Long): Flow<ScanRecord?>
```

This keeps the detail screen live while upload status changes from `PENDING` to `UPLOADING`, `FAILED`, or `UPLOADED`.

### Build Dependency

Updated:

```text
app/build.gradle.kts
```

The sample app now depends on `kotlinx-serialization-json` so it can pretty-print stored JSON in the detail screen.

## How To Use

1. Launch the sample app.
2. Run a security scan.
3. Wait for the scan to complete.
4. Tap `Open Scan Detail`.
5. Review upload status and raw JSON.
6. Use the copy actions when handing evidence to the backend teammate.

## Verification

Build command:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :app:assembleDebug
```

Result:

```text
BUILD SUCCESSFUL
```

## Phase 9 Status

Phase 9 is complete.

