# AEGIS Agent Phase 2 - Config Persistence

## What Changed

`AgentConfig` is now persisted locally when `AegisSdk.init()` is called.

The stored config is used to recover agent scheduling after process death, app package replacement, or device reboot.

## Files Added

`ConfigRepository.kt`

- Stores `AgentConfig` as JSON.
- Uses `EncryptedSharedPreferences`.
- Uses `MasterKey` with AES-256-GCM.
- Exposes synchronous `save`, `load`, and `clear` methods.

`AgentConfigHolderTest.kt`

- Verifies in-memory config wins when present.
- Verifies persisted config is loaded when memory is empty.

## Files Updated

`AegisSdk.kt`

- Persists config during `init`.
- Keeps `AgentConfigHolder` populated for Hilt providers.
- Clears persisted config during `shutdown`.
- Adds `initFromPersistedConfig` for reboot/package-replace recovery.

`BootReceiver.kt`

- Restores the agent from persisted config.
- No longer depends only on `AgentConfigHolder`.

`ScannerModule.kt`

- Reads config from memory first.
- Falls back to `ConfigRepository`.

`AppModule.kt`

- Reads BYOD mode from memory first.
- Falls back to `ConfigRepository`.

`libs.versions.toml` and `aegis-agent/build.gradle.kts`

- Add `androidx.security:security-crypto:1.1.0`.

## Current Behavior

1. Host app calls `AegisSdk.init(context, config)`.
2. Config is saved in encrypted preferences.
3. Config is also placed in `AgentConfigHolder`.
4. WorkManager schedules the scan worker.
5. If the process restarts, Hilt providers can reload config from storage.
6. If `BootReceiver` receives `BOOT_COMPLETED` or `MY_PACKAGE_REPLACED`, it calls `AegisSdk.initFromPersistedConfig`.
7. If `AegisSdk.shutdown(context)` is called, scheduled work is cancelled and persisted config is removed.

## Notes

AndroidX Security Crypto 1.1.0 deprecates its APIs in favor of direct platform Keystore use. For this POC agent phase, `EncryptedSharedPreferences` is acceptable because it gives us encrypted token persistence quickly and keeps the implementation small.

A later production hardening phase can replace this repository internals with direct Android Keystore encryption while keeping the same `ConfigRepository` interface.

## Verification

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```
