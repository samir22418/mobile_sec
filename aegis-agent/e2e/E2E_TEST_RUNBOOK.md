# AEGIS Agent — End-to-End Test Runbook

This runbook was prepared because the audit sandbox could not execute any
commands (Gradle, Python, emulator). Run these steps on your own machine
(Windows host with Android Studio + JDK 17 + Python 3 installed). Everything
here is read-only / additive — nothing is published or shipped.

There are three independent test tiers. Run them in order; each one is more
useful than the last but also more setup-heavy.

---

## Tier 1 — JVM unit tests for `:aegis-agent` (no emulator, ~1 min)

From the `aegis-agent/` project root (the folder containing `settings.gradle.kts`):

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\aegis-agent
.\gradlew :aegis-agent:test
```

What this validates:
- `RootDetectorTest`-style pure logic (su-binary / test-keys / Superuser.apk checks)
- `DeviceScannerTest` — scan orchestration, Play Integrity verdict mapping
- `AppIntelligenceCollectorTest` — install-source classification, delta diffing
- `LogFilterAgentTest` — buffering/flush thresholds, threat-regex matching
- `TelemetryUploaderTest` / `TelemetryPayloadTest` — payload serialization, stable payload IDs
- `UploadTelemetryUseCaseTest` — upload/retry bookkeeping
- `ScanRecordTest`, `AgentConfigHolderTest`

**Expected result:** all tests pass. Report is at
`aegis-agent/build/reports/tests/test/index.html` (or
`aegis-agent/aegis-agent/build/reports/tests/testDebugUnitTest/index.html`
depending on variant).

**If it fails:** capture the failing test class/method + stack trace — that's
higher-signal than anything in the static audit, since these tests exercise
real Android-adjacent logic (Robolectric-free, MockK-based).

---

## Tier 2 — POC telemetry server smoke test (no emulator, ~5 sec)

This validates the actual HTTP contract the agent talks to, using a scripted
client instead of a real device.

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\aegis-agent\poc-server
bash ..\e2e\run_poc_e2e.sh
```

(If you don't have `bash`/`curl` on Windows: use Git Bash, or WSL, or ask me
to translate `run_poc_e2e.sh` into a Python script — `requests` would work
identically.)

The script:
1. Starts `aegis_poc_server.py` in the background on `127.0.0.1:8080`
2. Hits `GET /health` → expects `{"ok": true, ...}`
3. POSTs `e2e/sample_telemetry_payload.json` (shaped exactly like
   `TelemetryPayload` from `domain/model/TelemetryPayload.kt`, including
   `device_report`, `app_snapshot`, `important_logs`) → expects `202 accepted`
4. Confirms the record landed in `telemetry.jsonl`
5. Toggles `/fail?enabled=true`, retries → expects `500`, then disables and
   retries → expects `202` (mirrors `TelemetrySyncWorker`'s `Result.retry()` path)
6. Sends malformed/missing-field payloads → expects `400`, and an unknown
   route → expects `404`

**⚠️ Known contract mismatch to verify while you're at it:**
`poc-server/telemetry_schema_v1.json` lists `enrollment_token` as a
**required top-level field** in the JSON body. But `TelemetryPayload.kt` and
`TelemetryUploader.kt` never put the enrollment token in the body — it's
sent only as the `Authorization: Bearer <token>` header (which is actually
the *better* practice, per the comment in `TelemetryPayload.kt`). The actual
`aegis_poc_server.py` handler does **not** enforce `enrollment_token` or
`important_logs` as required (its `missing` check only looks at
`payload_id`, `scan_id`, `device_id`, `device_report`, `app_snapshot`), so
the real server is more permissive than its own documented schema. This is
a documentation/schema drift bug — either update
`telemetry_schema_v1.json` to drop `enrollment_token` from `required` (and
document the header-based auth instead), or decide the body should carry it
and update the Kotlin models + uploader to match. Worth a real ticket.

---

## Tier 3 — Sample app + emulator (requires Android Studio, on your machine)

**Blocker found during the static audit:** `aegis-agent/app/src/main/` has no
`AndroidManifest.xml` and no Kotlin source (`MainActivity.kt`,
`SampleApp.kt`, etc.) even though `app/build.gradle.kts`, layout XML, and
stale `build/` artifacts reference them. **This module will not build until
that source is restored** (or the module is removed from
`settings.gradle.kts`). Check whether those files exist in your local
checkout but weren't visible to this session, or whether they need to be
recovered from version control / regenerated.

Once `:app` builds:

1. Open the project in Android Studio (`aegis-agent/` root, JDK 17).
2. Set `local.properties`:
   ```
   AEGIS_BACKEND_URL=http://10.0.2.2:8080
   AEGIS_CLOUD_PROJECT_NUMBER=0
   ```
   (`10.0.2.2` is how the Android emulator reaches your host's `127.0.0.1`,
   so it can talk to the POC server from Tier 2.)
3. Start the POC server (Tier 2, step 1) on your host, listening on
   `0.0.0.0:8080` so the emulator can reach it:
   ```powershell
   python aegis_poc_server.py --host 0.0.0.0 --port 8080
   ```
4. Create/launch an AVD (API 34, x86_64, Google Play image — minSdk is 26,
   targetSdk 34).
5. Run `:app` on the emulator.
6. In the running app:
   - Trigger `AegisSdk.init(...)` with the POC backend URL and a dummy
     enrollment token, then call `requestScanNow()`.
   - Confirm a scan record appears (Room DB — pull via Android Studio's
     **App Inspection → Database Inspector** to view `scan_records`).
   - Confirm a row lands in the POC server's `telemetry.jsonl` after
     `TelemetrySyncWorker` runs (WorkManager — you can force it via
     `adb shell cmd jobscheduler run -f com.aegis.agent.sample <jobId>` or
     just wait for the periodic interval).
   - Check **Logcat** for `AEGIS Agent initialised` (Timber debug tree) and
     no uncaught exceptions.
7. Root-detection check: on a non-rooted emulator,
   `root_detection.is_rooted` should be `false`. (Testing the `true` path
   requires a rooted AVD image or mocking `RootDetector` — not safe/needed
   for this audit.)
8. Cert-pinning check (relates to Layer 8 finding): with the placeholder
   pins currently in `NetworkModule.kt`, pinning is disabled, so HTTPS to
   `AEGIS_BACKEND_URL` should succeed normally. If you later populate real
   pins, re-test against the POC server (which is plain HTTP — pinning only
   applies to HTTPS, so use a TLS-terminating proxy or an HTTPS POC endpoint
   to verify pin enforcement).

---

## What to send back to me

- Tier 1: paste any failing test names + stack traces, or just say "all
  green."
- Tier 2: paste the script's final output (especially if any step printed
  `FAIL:`).
- Tier 3: screenshots/logcat snippets of the init → scan → upload flow, plus
  whatever you find about the missing `app/src/main` source.

I'll fold the results into the audit findings and re-prioritize the Top 5
issues if anything new turns up.
