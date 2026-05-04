# AEGIS Agent Phase 10 - Log Agent Integration

## Purpose

Phase 10 connects the existing log filter into the scan/upload loop.

Important logs are now captured during a worker scan, persisted with the scan record, rebuilt during retry, and uploaded inside `TelemetryPayload.important_logs`.

## Implementation

Updated:

```text
aegis-agent/src/main/java/com/aegis/agent/data/logs/LogFilterAgent.kt
aegis-agent/src/main/java/com/aegis/agent/data/worker/TelemetrySyncWorker.kt
aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanResultRepository.kt
aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanRecordEntity.kt
aegis-agent/src/main/java/com/aegis/agent/domain/model/ScanRecord.kt
aegis-agent/src/main/java/com/aegis/agent/domain/usecase/UploadTelemetryUseCase.kt
```

The worker now:

1. collects device posture
2. collects app inventory
3. opens a short log capture window
4. stores important logs with the scan
5. uploads the payload

## Worker-Scoped Lifecycle

The chosen lifecycle is worker-only for this POC:

```text
TelemetrySyncWorker
  -> LogFilterAgent.collectSnapshot()
  -> logcat reader starts
  -> ImportanceFilter keeps security-relevant lines
  -> bounded list returned
  -> logcat reader stops
```

This avoids a permanent background log process and keeps log evidence tied to a specific scan payload.

Defaults:

```text
snapshot window: 2 seconds
max logs per payload: 50
buffer max: 200
buffer TTL: 10 minutes
```

## Persistence

Room moved from version 4 to version 5.

Migration:

```text
important_log_count INTEGER NOT NULL DEFAULT 0
important_logs_json TEXT
```

This is necessary because upload retry must rebuild the same payload later. If logs were only held in memory, retries would lose evidence or produce different payload contents.

## Upload Contract

`TelemetryPayload.important_logs` is now populated from persisted scan data.

Each log has:

```text
id
timestamp_epoch_ms
device_id
tag
level
message
matched_rule
```

`matched_rule` explains why the agent retained the log:

```text
TAG_KEYWORD
LEVEL_ERROR_OR_ASSERT
THREAT_REGEX
```

## Sample App Debug UI

Updated:

```text
app/src/main/java/com/aegis/agent/sample/ui/MainActivity.kt
app/src/main/java/com/aegis/agent/sample/ui/ScanDetailActivity.kt
app/src/main/res/layout/activity_main.xml
app/src/main/res/layout/activity_scan_detail.xml
```

The dashboard now shows important log count.

The detail screen now shows important log count, full logs JSON, and a copy action for backend handoff/debugging.

## Android Limitation

Normal production Android apps cannot read all system logs. Logcat visibility is restricted by app UID, device policy, debug state, privileges, and OEM behavior.

Treat this log batch as best-effort:

- useful on emulator/debug/enterprise/privileged builds
- not guaranteed to include global system logs on unmanaged production devices
- server models must handle empty `important_logs`

## Verification

Commands:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```

Result:

```text
BUILD SUCCESSFUL
```

## Phase 10 Status

Phase 10 is complete.

