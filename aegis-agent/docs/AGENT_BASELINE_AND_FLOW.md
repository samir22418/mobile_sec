# AEGIS Agent Baseline And Flow

## Baseline Status

Validated on the local machine with Android Studio JBR:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```

Both commands pass.

The default shell Java currently points to a JRE-only Temurin install:

```text
C:\Program Files\Eclipse Adoptium\jre-17.0.8.101-hotspot
```

Use the Android Studio JBR or another full JDK when running Gradle.

## Current Agent Lifecycle

1. Host app calls `AegisSdk.init(context, config)`.
2. `AegisSdk` stores `AgentConfig` in `AgentConfigHolder`.
3. `AegisSdk` schedules periodic `TelemetrySyncWorker` work through WorkManager.
4. The sample app can also call `AegisSdk.requestScanNow()` for a manual scan.
5. `TelemetrySyncWorker` creates a `RUNNING` scan record in Room.
6. The worker calls `CollectDeviceTelemetryUseCase`.
7. `CollectDeviceTelemetryUseCase` calls `DeviceScanner.scan()`.
8. `DeviceScanner` collects root signals, Play Integrity result, security patch date, and bootloader state.
9. The worker calls `CollectAppInventoryUseCase`.
10. `CollectAppInventoryUseCase` calls `AppIntelligenceCollector.collect()`.
11. `AppIntelligenceCollector` builds a full or delta app snapshot.
12. The worker persists a `SUCCESS` scan record with summary fields, full JSON payloads, `payloadId`, and `uploadStatus=PENDING`.
13. `UploadTelemetryUseCase` drains pending/failed upload records.
14. `TelemetryUploader` POSTs payloads to `{backendUrl}/api/v1/telemetry`.
15. `ScanResultRepository` marks rows `UPLOADED` or `FAILED`.
16. `MainActivity` observes the latest scan record through `ScanResultRepository.observeLatest()`.

## Important Current Gaps

The agent can upload telemetry to the POC endpoint when `AEGIS_BACKEND_URL` points at a reachable server.

Config is now persisted through `ConfigRepository`. `BootReceiver` can recover scheduling from encrypted local storage.

`LogFilterAgent` is implemented and provided by Hilt, but no production path starts it or includes logs in scan records.

The scan database keeps full JSON, stable payload IDs, upload status, and retry metadata.

## Next Agent-First Work

1. Perform emulator end-to-end upload/retry testing.
2. Add scan detail UI for upload state debugging.
3. Integrate logs after the core upload loop is stable.
