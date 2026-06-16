# AEGIS Agent — Project Analysis & Completion Plan

## Current State Summary

The project is an **Android EDR (Endpoint Detection & Response) agent** built as a library module (`:aegis-agent`) with a sample host app (`:app`). It follows clean architecture with **data → domain → presentation** layers.

### ✅ What's Already Built & Working

| Component | Files | Status |
|---|---|---|
| **SDK Entry Point** | `AegisSdk.kt`, `AegisApplication.kt` | ✅ Working — init, shutdown, manual scan |
| **Device Scanner** | `DeviceScanner.kt`, `RootDetector.kt`, `IntegrityApiClient.kt` | ✅ Working — root detection, Play Integrity, patch date, bootloader |
| **App Intelligence** | `AppIntelligenceCollector.kt`, `PackageEventReceiver.kt` | ✅ Working — full/delta scans, SHA-256 hashing, install source classification |
| **Log Filter Agent** | `LogFilterAgent.kt`, `ImportanceFilter.kt`, `LogcatReader.kt` | ✅ Built but **not wired** into scan pipeline |
| **Background Worker** | `TelemetrySyncWorker.kt` | ✅ Working — runs device + app scans, persists results |
| **Scan Persistence** | `ScanResultRepository.kt`, `AegisDatabase.kt`, `ScanRecordDao.kt`, `ScanRecordEntity.kt` | ✅ Working — Room DB stores last 25 scan records |
| **DI Modules** | `ScannerModule.kt`, `AppModule.kt`, `LogModule.kt`, `NetworkModule.kt`, `PersistenceModule.kt` | ✅ Working — all Hilt modules wired |
| **Domain Models** | `DeviceReport.kt`, `AppInfo.kt`, `ImportantLog.kt`, `ScanRecord.kt`, `AgentConfig.kt` | ✅ Complete |
| **Use Cases** | `CollectDeviceTelemetryUseCase.kt`, `CollectAppInventoryUseCase.kt` | ✅ Working |
| **Sample App** | `SampleApp.kt`, `MainActivity.kt`, `activity_main.xml` | ✅ Working — dashboard with scan button |
| **System** | `BootReceiver.kt` | ✅ Working — reschedules after reboot |
| **Unit Tests** | `DeviceScannerTest.kt`, `LogFilterAgentTest.kt`, `AppIntelligenceCollectorTest.kt` | ⚠️ Exist but may need fixes |
| **Docs** | `aegis-project-guide.md`, `scan-persistence-and-dashboard.md` | ✅ Good documentation |

---

## 🔴 What's Missing (5 Features to Complete)

These come directly from the project's own `aegis-project-guide.md` § 9–10 and from `TelemetrySyncWorker.kt` line 71 (`// Prompt 2.1: uploadTelemetry`):

### Phase 1: Backend Upload & Retry Queue
**Priority: HIGH** — The entire agent collects data but never sends it anywhere.

### Phase 2: Encrypted Config Persistence
**Priority: HIGH** — `AgentConfigHolder` is in-memory only; config is lost on process death.

### Phase 3: Log Agent Integration
**Priority: MEDIUM** — `LogFilterAgent` is fully built but never started by the SDK or worker.

### Phase 4: Scan Details Screen
**Priority: MEDIUM** — The dashboard shows summary only; no way to view full JSON payloads.

### Phase 5: Unit Test Verification & Fixes
**Priority: MEDIUM** — Tests exist but haven't been verified after recent code changes.

---

## Proposed Changes

---

### Phase 1: Backend Upload & Retry Queue

Upload collected `DeviceReport`, `AppSnapshot`, and `ImportantLog` batches to the AEGIS backend via OkHttp with certificate pinning.

#### [NEW] [TelemetryUploader.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/network/TelemetryUploader.kt)
- HTTP POST to `{backendUrl}/api/v1/telemetry`
- Sends device report + app snapshot + log batch as a single JSON payload
- Uses the existing `OkHttpClient` from `NetworkModule` (already has cert pinning)
- Returns `Result<Unit>` — success or a typed error

#### [NEW] [UploadTelemetryUseCase.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/domain/usecase/UploadTelemetryUseCase.kt)
- Domain-layer interactor that calls `TelemetryUploader`
- Wraps result in `kotlin.Result`

#### [NEW] [TelemetryPayload.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/domain/model/TelemetryPayload.kt)
- `@Serializable` data class combining `DeviceReport` + `AppSnapshot` + `List<ImportantLog>`
- Includes `enrollmentToken` and timestamp

#### [MODIFY] [TelemetrySyncWorker.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/worker/TelemetrySyncWorker.kt)
- Replace the `// Prompt 2.1: uploadTelemetry(...)` comment with actual upload call
- On upload failure: save to Room for retry on next cycle
- Add `uploaded` boolean flag to `ScanRecordEntity`

#### [MODIFY] [ScanRecordEntity.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanRecordEntity.kt)
- Add `uploaded: Boolean = false` column
- Increment Room DB version to 2

#### [MODIFY] [ScanRecordDao.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanRecordDao.kt)
- Add `getUnuploaded(): List<ScanRecordEntity>` query
- Add `markUploaded(id: Long)` update

#### [MODIFY] [AegisDatabase.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/persistence/AegisDatabase.kt)
- Add Room migration from version 1 → 2

---

### Phase 2: Encrypted Config Persistence

Replace in-memory `AgentConfigHolder` with encrypted persistent storage using `EncryptedSharedPreferences`.

#### [NEW] [ConfigRepository.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/persistence/ConfigRepository.kt)
- Read/write `AgentConfig` to `EncryptedSharedPreferences`
- Uses AndroidX Security Crypto library
- Auto-loads config on process start (before Hilt graph is ready)

#### [MODIFY] [ScannerModule.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/di/ScannerModule.kt)
- `AgentConfigHolder` reads from `ConfigRepository` if in-memory config is null

#### [MODIFY] [AegisSdk.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/AegisSdk.kt)
- `init()` persists config to `ConfigRepository` after setting `AgentConfigHolder`
- `BootReceiver` can now reload config without the host app calling init again

#### [MODIFY] [build.gradle.kts](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/build.gradle.kts)
- Add `androidx.security:security-crypto:1.1.0-alpha06` dependency

#### [MODIFY] [libs.versions.toml](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/gradle/libs.versions.toml)
- Add security-crypto version and library entry

---

### Phase 3: Log Agent Integration

Wire `LogFilterAgent` into the scan pipeline so security logs are collected and included in uploads.

#### [MODIFY] [TelemetrySyncWorker.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/worker/TelemetrySyncWorker.kt)
- Inject `LogFilterAgent`
- Call `logFilterAgent.start()` at the beginning of the scan
- Flush and collect buffered logs after device + app scans complete
- Include log batch in the upload payload

#### [MODIFY] [AegisSdk.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/AegisSdk.kt)
- Start `LogFilterAgent` during `init()` for continuous background monitoring
- Stop it during `shutdown()`

#### [MODIFY] [ScanRecordEntity.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/main/java/com/aegis/agent/data/persistence/ScanRecordEntity.kt)
- Add `logCount: Int?` and `logBatchJson: String?` columns

---

### Phase 4: Scan Details Screen

Add a second Activity that shows the full JSON payload of a completed scan record.

#### [NEW] [ScanDetailActivity.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/app/src/main/java/com/aegis/agent/sample/ui/ScanDetailActivity.kt)
- Receives scan record ID via Intent extra
- Loads full `deviceReportJson` and `appSnapshotJson` from Room
- Displays formatted JSON in a scrollable view with syntax highlighting
- Copy-to-clipboard button

#### [NEW] [activity_scan_detail.xml](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/app/src/main/res/layout/activity_scan_detail.xml)
- Dark theme matching the dashboard
- Tabs for Device Report / App Snapshot / Logs

#### [MODIFY] [MainActivity.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/app/src/main/java/com/aegis/agent/sample/ui/MainActivity.kt)
- Add click handler on the status card to navigate to `ScanDetailActivity`

#### [MODIFY] [AndroidManifest.xml](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/app/src/main/AndroidManifest.xml)
- Register `ScanDetailActivity`

---

### Phase 5: Unit Test Verification & Fixes

#### [MODIFY] [DeviceScannerTest.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/test/java/com/aegis/agent/data/scanner/DeviceScannerTest.kt)
- Update mocks for the `CoroutineDispatcher` parameter added to `DeviceScanner`
- Verify tests pass with `Dispatchers.Unconfined` for the main dispatcher

#### [MODIFY] [LogFilterAgentTest.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/test/java/com/aegis/agent/data/logs/LogFilterAgentTest.kt)
- Verify all 6 nested test classes pass

#### [MODIFY] [AppIntelligenceCollectorTest.kt](file:///c:/Users/ASUS/Desktop/mobile_sec/aegis-agent/aegis-agent/src/test/java/com/aegis/agent/data/apps/AppIntelligenceCollectorTest.kt)
- Verify all install source, APK hash, cert hash, and model tests pass

---

## Open Questions

> [!IMPORTANT]
> **Backend API contract:** The upload endpoint (`/api/v1/telemetry`) doesn't exist yet. Should I create a mock server endpoint in the sample app for testing, or just implement the client-side code and test against a local server you provide?

> [!IMPORTANT]  
> **Phase priority:** Do you want me to implement all 5 phases, or focus on specific ones first? The phases are ordered by importance but each is independent.

> [!WARNING]
> **EncryptedSharedPreferences** requires `minSdk 23` (you have 26, so this is fine) and adds the `security-crypto` dependency (~50 KB). Is this acceptable, or do you prefer a different persistence approach?

---

## Verification Plan

### Automated Tests
- Run `gradlew :aegis-agent:testDebugUnitTest` after each phase
- Verify all existing + new tests pass
- Run `gradlew :app:assembleDebug` to confirm the sample app compiles

### Manual Verification
- Deploy to emulator/device and tap "Run Security Scan"
- Watch Logcat for the full scan → upload → success flow
- Verify scan detail screen shows formatted JSON
- Kill the app process and verify config survives restart via `BootReceiver`
# Status Note

This document is historical as of 2026-05-28. The active backend, Android upload
flow, encrypted config persistence, log integration, scan details screen,
dashboard, and end-to-end emulator path have since been implemented. Use
`docs/backend-android-next-implementation-stages.md` for the current plan.
