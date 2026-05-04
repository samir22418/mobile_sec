# AEGIS Agent Phase 8 - Emulator End-To-End Upload And Retry Results

## Purpose

Phase 8 proves the agent-side POC loop on a real Android emulator:

```text
Sample app -> AegisSdk -> WorkManager -> Room upload queue -> HTTP uploader -> POC server -> JSONL
```

The server is still intentionally only a POC receiver. The phase validates the Android agent behavior that the backend teammate will later integrate against.

## Environment

Repo:

```text
C:\Users\ASUS\Desktop\mobile_sec\aegis-agent
```

Emulator:

```text
Medium_Phone_API_36.1
emulator-5554
```

POC server:

```text
http://127.0.0.1:8080
```

Sample app backend URL:

```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
```

Android package:

```text
com.aegis.agent.sample
```

Telemetry file:

```text
poc-server-data/telemetry.jsonl
```

## Setup Commands

Use Android Studio's bundled JDK:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
```

Start the POC server:

```powershell
python .\poc-server\aegis_poc_server.py --host 0.0.0.0 --port 8080 --output-dir .\poc-server-data
```

Start the emulator:

```powershell
emulator.exe -avd Medium_Phone_API_36.1 -no-snapshot-save -no-boot-anim -no-audio -no-window
```

Build and install:

```powershell
.\gradlew.bat :app:assembleDebug
adb install -r .\app\build\outputs\apk\debug\app-debug.apk
adb shell pm clear com.aegis.agent.sample
adb shell am start -n com.aegis.agent.sample/.ui.MainActivity
```

The app button bounds in this emulator were:

```text
[100,625][980,762]
```

Useful tap coordinate:

```powershell
adb shell input tap 540 690
```

## Success Path Result

Server forced failure was disabled:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=false
```

The first scan uploaded successfully.

Observed payload:

```text
payload_id: c9c9ebeb-23db-311a-bd25-9b74887d3e14
device_id: sample-device-001
app_count: 251
HTTP: 202 Accepted
```

Important log evidence:

```text
TelemetryUploader: uploaded payload=c9c9ebeb-23db-311a-bd25-9b74887d3e14
TelemetrySyncWorker: upload drain complete; attempted=1 uploaded=1 failed=0
Worker result SUCCESS
```

Server evidence:

```text
poc-server-data/telemetry.jsonl line count: 1
```

## Forced Failure Result

Forced failure was enabled:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=true
adb logcat -c
adb shell input tap 540 690
```

The agent completed the scan, tried to upload, received HTTP 500, marked the upload as failed, kept it queued, and returned WorkManager retry.

Observed failed payload:

```text
payload_id: ecabcbfa-20d7-31da-b6d3-cc54402ac665
scan_id: 2
HTTP: 500 Internal Server Error
server body: {"error":"forced_failure"}
```

Important log evidence:

```text
OkHttp: <-- 500 Internal Server Error http://10.0.2.2:8080/api/v1/telemetry
UploadTelemetryUseCase: upload failed for scan=2
TelemetrySyncWorker: upload drain complete; attempted=1 uploaded=0 failed=1
TelemetrySyncWorker: upload failures remain queued; will retry
Worker result RETRY
```

Server evidence:

```text
poc-server-data/telemetry.jsonl line count stayed at 1
```

That confirms the server did not accept or append the failed request.

## Recovery Result

Forced failure was disabled:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=false
adb logcat -c
adb shell input tap 540 690
```

The next worker run drained the queue. It uploaded the previously failed payload first, then uploaded the new scan.

Observed payloads:

```text
recovered payload: ecabcbfa-20d7-31da-b6d3-cc54402ac665
new payload:       a9e02e91-915d-3752-ae09-d88262adf206
HTTP:              202 Accepted for both uploads
```

Important log evidence:

```text
TelemetryUploader: uploaded payload=ecabcbfa-20d7-31da-b6d3-cc54402ac665
TelemetryUploader: uploaded payload=a9e02e91-915d-3752-ae09-d88262adf206
TelemetrySyncWorker: upload drain complete; attempted=2 uploaded=2 failed=0
Worker result SUCCESS
```

Server evidence:

```text
poc-server-data/telemetry.jsonl line count: 3
```

Payload IDs in the JSONL file:

```text
c9c9ebeb-23db-311a-bd25-9b74887d3e14
ecabcbfa-20d7-31da-b6d3-cc54402ac665
a9e02e91-915d-3752-ae09-d88262adf206
```

## What This Proves

Phase 8 confirms:

- the emulator can reach the host POC server through `10.0.2.2`
- the sample app config reaches the agent
- WorkManager can run manual and periodic agent work
- scans persist to Room
- successful scans become upload candidates
- upload payloads are accepted by the POC server
- failed HTTP uploads remain queued
- WorkManager returns `RETRY` when upload failures remain
- a later healthy run drains failed uploads before finishing successfully
- `payload_id` is stable enough for retry/idempotency testing

## Notes

The forced failure request does not append telemetry to JSONL. That makes the JSONL line count a clean signal:

```text
1 line after success
1 line after forced failure
3 lines after recovery
```

The recovery run uploaded two payloads because the queue contained the previous failed scan plus the newly completed scan.

## Phase 8 Status

Phase 8 is complete.

