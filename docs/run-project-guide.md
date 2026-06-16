# AEGIS Agent Run Guide

## 1. Open Project Folder

Use PowerShell:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\aegis-agent
```

## 2. Set Java

Gradle needs a full JDK. Use Android Studio's bundled JDK:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
```

## 3. Build And Test

Run:

```powershell
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```

Expected result:

```text
BUILD SUCCESSFUL
```

## 4. Configure Backend URL

Make sure `local.properties` contains:

```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
```

`10.0.2.2` lets the Android emulator reach the host machine.

## 5. Start Local Backend MVP

From the repository root, start the FastAPI backend, Ollama-backed local AI
analyzers, and React dashboard:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec
.\tools\start_local_mvp.ps1
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
```

Dashboard:

```text
http://127.0.0.1:5173/
```

Token admin page:

```text
http://127.0.0.1:8080/
```

## 6. Start Emulator

Use the available AVD:

```powershell
emulator.exe -avd Medium_Phone_API_36.1
```

Check device:

```powershell
adb devices
```

Expected:

```text
emulator-5554	device
```

## 7. Install And Launch App

```powershell
adb install -r .\app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.aegis.agent.sample/.ui.MainActivity
```

Optional clean start:

```powershell
adb shell pm clear com.aegis.agent.sample
adb shell am start -n com.aegis.agent.sample/.ui.MainActivity
```

## 8. Use The App

In the sample app:

1. Tap `Run Security Scan`.
2. Wait for completion.
3. Review the dashboard:
   - local risk score
   - upload status
   - payload ID
   - important log count
   - recent scans
   - AI model runs and risk decision trace
4. Tap `Open Scan Detail`.
5. Review:
   - analyst brief
   - device JSON
   - app snapshot JSON
   - important logs JSON
6. Use copy actions when sharing evidence with the backend/data engineer.

## 9. Check Uploaded Telemetry

Telemetry is stored in the local backend database and raw payload folder:

```text
backend-data/aegis.db
backend-data/raw-payloads/
```

Check devices through the API:

```powershell
$headers = @{ Authorization = 'Bearer sample-token' }
Invoke-RestMethod `
  -Uri 'http://127.0.0.1:8080/api/v1/devices' `
  -Headers $headers
```

Check the latest uploaded device:

```powershell
Invoke-RestMethod `
  -Uri 'http://127.0.0.1:8080/api/v1/devices/sample-device-001/latest-risk' `
  -Headers $headers
```

## 10. Test Retry Behavior

This retry check is still easiest against the legacy POC server. For the current
backend MVP, stop the API process, run a scan, then start the API again and wait
for WorkManager to retry.

Legacy POC forced failure:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=true
```

Run another scan in the app.

Expected:

- upload returns HTTP 500
- scan remains queued
- WorkManager retries later
- JSONL line count does not increase

Disable failure:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/fail?enabled=false
```

Run another scan.

Expected:

- previous failed payload uploads first
- new payload uploads after it
- JSONL line count increases

## 11. Useful Logcat Filter

```powershell
adb logcat -d | Select-String -Pattern 'TelemetrySyncWorker|UploadTelemetryUseCase|TelemetryUploader|LogFilterAgent|WM-WorkerWrapper|OkHttp'
```

Clear logcat:

```powershell
adb logcat -c
```

## 12. Important Files

Agent:

```text
aegis-agent/src/main/java/com/aegis/agent
```

Sample app:

```text
app/src/main/java/com/aegis/agent/sample
```

POC server:

```text
poc-server/aegis_poc_server.py
```

Telemetry schema:

```text
poc-server/telemetry_schema_v1.json
```

Backend handoff:

```text
backend-data-engineering-handoff.md
```

Final handoff:

```text
agent-implementation-handoff.md
```
