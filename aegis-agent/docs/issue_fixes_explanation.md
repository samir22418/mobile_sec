# Issue Fixes Explanation

Date: 2026-04-27

This document explains the fixes applied after reviewing and testing the AEGIS
Android agent project. The goal was to solve the concrete issues found in the
library and make the reason for each change clear for future development.

## 1. DataStore fingerprint loading could hang

File changed:

- `aegis-agent/src/main/java/com/aegis/agent/data/apps/AppIntelligenceCollector.kt`

Problem:

`loadPreviousFingerprints()` used `dataStore.data.collect { ... }` to read the
stored app fingerprint set. `DataStore.data` is a continuous Flow, so collecting
it directly can keep waiting forever. That makes `collect()` risk hanging before
it can calculate the app inventory delta.

Fix:

The code now uses `dataStore.data.first()` to read exactly one snapshot from
DataStore and continue. This matches the use case: the collector only needs the
current stored fingerprint set before comparing it with the new scan.

## 2. BootReceiver was declared but missing

Files changed:

- `aegis-agent/src/main/AndroidManifest.xml`
- `aegis-agent/src/main/java/com/aegis/agent/data/system/BootReceiver.kt`

Problem:

The library manifest declared `.data.system.BootReceiver`, but no Kotlin class
existed at that path. A broadcast to that receiver could fail at runtime because
Android would try to instantiate a missing class.

Fix:

Added `BootReceiver`. It listens for `BOOT_COMPLETED` and
`MY_PACKAGE_REPLACED`, checks whether `AgentConfigHolder` already has runtime
configuration, and calls `AegisSdk.init()` again when possible.

Important limitation:

The SDK configuration is still stored in memory only. After a real device reboot,
the config may not exist until the host app initializes the SDK again. The new
receiver handles that safely by logging the situation instead of crashing. A
future enrollment stage should persist the config securely if reboot-time
rescheduling must work without host app startup.

## 3. Tests needed JUnit parameterized support

Files changed:

- `gradle/libs.versions.toml`
- `aegis-agent/build.gradle.kts`

Problem:

The unit tests import `org.junit.jupiter.params.ParameterizedTest`,
`ValueSource`, and `CsvSource`, but the project only declared `junit-jupiter-api`
and `junit-jupiter-engine`.

Fix:

Added `junit-jupiter-params` to the version catalog and included it as a
`testImplementation` dependency for the library module.

## 4. DataStore mock did not match the real API path

File changed:

- `aegis-agent/src/test/java/com/aegis/agent/data/apps/AppIntelligenceCollectorTest.kt`

Problem:

The test tried to mock `mockDataStore.edit(any())`. The production code uses the
DataStore Preferences `edit` extension, which delegates to the `DataStore`
member function `updateData()`. Mocking the extension directly was not the right
API boundary and caused test compilation problems.

Fix:

The test now mocks `mockDataStore.updateData(any())`, which is the function that
the extension calls underneath.

## 5. Android framework string fields were null in local JVM tests

Files changed:

- `aegis-agent/src/main/java/com/aegis/agent/data/scanner/RootDetector.kt`
- `aegis-agent/src/main/java/com/aegis/agent/data/scanner/DeviceScanner.kt`

Problem:

Local JVM unit tests run against Android SDK stubs, not a real device. In that
environment, fields like `Build.TAGS` and `Build.VERSION.SECURITY_PATCH` can be
null even though production Android devices normally provide string values.

Fix:

`RootDetector.isTestKeysBuild()` now accepts a nullable string and treats null as
"not test keys". `DeviceScanner.readSecurityPatchDate()` now safely returns
`"unknown"` when the security patch field is null or blank.

## 6. DeviceScanner hardcoded the Android main dispatcher

Files changed:

- `aegis-agent/src/main/java/com/aegis/agent/data/scanner/DeviceScanner.kt`
- `aegis-agent/src/test/java/com/aegis/agent/data/scanner/DeviceScannerTest.kt`

Problem:

`DeviceScanner.scan()` switches to `Dispatchers.Main` before calling Play
Integrity. That is reasonable on Android, but local JVM tests do not have an
Android main looper, so the tests failed.

Fix:

`DeviceScanner` now accepts an injectable `mainDispatcher` with a production
default of `Dispatchers.Main`. Tests pass a test dispatcher. Production behavior
is unchanged, but the scanner is now easier to test.

## 7. Base64 handling used Android-only APIs

Files changed:

- `aegis-agent/src/main/java/com/aegis/agent/data/scanner/DeviceScanner.kt`
- `aegis-agent/src/main/java/com/aegis/agent/data/scanner/IntegrityApiClient.kt`

Problem:

The scanner and integrity token parser used `android.util.Base64`. That works on
devices, but it throws in local JVM unit tests because it is part of the Android
framework stubs.

Fix:

The code now uses `java.util.Base64`, which is available both in local JVM tests
and on Android API 26+.

## 8. LogFilterAgent tests had long-running coroutine jobs

Files changed:

- `aegis-agent/src/main/java/com/aegis/agent/data/logs/LogFilterAgent.kt`
- `aegis-agent/src/test/java/com/aegis/agent/data/logs/LogFilterAgentTest.kt`

Problem:

`LogFilterAgent.start()` launched long-lived reader and flusher jobs using
hardcoded dispatchers. The tests could not control those jobs with virtual time,
which caused unfinished coroutine failures.

Fix:

`LogFilterAgent` now launches jobs on the injected scope instead of overriding
the dispatcher internally. Production still gets a Default-backed scope from
`LogModule`, while tests use `backgroundScope` so long-running work is expected
and automatically cleaned up by the coroutine test framework.

`stop()` was also simplified to cancel jobs and clear the buffer synchronously,
avoiding an extra cleanup coroutine.

## 9. One log test expected the wrong matched rule

File changed:

- `aegis-agent/src/test/java/com/aegis/agent/data/logs/LogFilterAgentTest.kt`

Problem:

The test named "ImportantLog contains correct fields after filter pass" expected
`LEVEL_ERROR_OR_ASSERT`, but it used the tag `AuthService`. Because `AUTH` is a
security keyword, the filter correctly matched `TAG_KEYWORD` first.

Fix:

The fixture now uses the benign tag `ActivityManager` with an ERROR level. That
tests the level rule without accidentally triggering the higher-priority tag
rule.

## Verification

All verification commands were run with:

`JAVA_HOME=C:\Program Files\Android\Android Studio\jbr`

Results:

- `.\gradlew.bat :aegis-agent:testDebugUnitTest --no-daemon` passed.
- `.\gradlew.bat :aegis-agent:assembleDebug --no-daemon` passed.
- `.\gradlew.bat :app:assembleDebug --no-daemon` passed.

Note:

The machine's default `java` command points to an Eclipse Adoptium JRE, which
does not include a Java compiler. Gradle needs a full JDK. Use the Android
Studio bundled JDK path above or install/configure a full JDK 17+.
