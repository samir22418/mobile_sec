# AEGIS Mobile Security Scanner

AEGIS is an Android mobile security scanner and lightweight EDR proof of concept.
It collects local device posture, app inventory, selected security logs, and upload
state so a backend/data engineering team can validate, enrich, and process the
telemetry later.

The current focus is the Android agent and sample scanner UI. The backend in this
repository is intentionally a small proof-of-concept server, not the final
production backend.

## What Is Included

- Android security agent library in `aegis-agent/aegis-agent`
- Sample Android scanner app in `aegis-agent/app`
- Local Room persistence for scan records
- WorkManager upload queue and retry flow
- Play Integrity token collection state
- Root, bootloader, patch, app inventory, and important log signals
- Local risk brief and analyst-friendly scan detail UI
- Dark/light theme support
- POC telemetry server in `aegis-agent/poc-server`
- Backend/data engineer handoff documentation in `docs`

## Important Integrity Note

If Google Play Integrity returns a token, the UI shows the device as
`Partially verified`.

That means the Android app received a Play Integrity token, but final trust still
requires backend validation. The client does not decode or fully trust the token
locally.

## Repository Layout

```text
mobile_sec/
  README.md
  aegis-agent/
    aegis-agent/      Android agent library
    app/              Sample scanner app
    poc-server/       Python POC telemetry receiver
    gradle/           Android build configuration
  docs/               Project guides, phases, handoff notes
```

## Quick Start

Open PowerShell in the Android project:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\aegis-agent
```

Set Java to Android Studio's bundled JDK:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
```

Build and test:

```powershell
.\gradlew.bat :aegis-agent:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```

Start the POC server:

```powershell
python .\poc-server\aegis_poc_server.py --host 0.0.0.0 --port 8080 --output-dir .\poc-server-data
```

Install and launch the sample app on an emulator:

```powershell
adb install -r .\app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.aegis.agent.sample/.ui.MainActivity
```

## Configuration

For emulator uploads to the local POC server, make sure
`aegis-agent/local.properties` contains:

```properties
AEGIS_BACKEND_URL=http://10.0.2.2:8080
```

For real Play Integrity testing, add your numeric Google Cloud project number:

```properties
AEGIS_CLOUD_PROJECT_NUMBER=123456789012
```

## Main User Flow

1. Run the POC server.
2. Build and install the Android sample app.
3. Open the scanner UI.
4. Tap `Run Security Scan`.
5. Review the dashboard risk score, upload state, and recommended action.
6. Open scan details for device posture, app inventory, logs, and JSON evidence.
7. Share or copy the analyst brief for backend/data engineering review.

## Useful Documentation

- [Run Project Guide](docs/run-project-guide.md)
- [Agent Implementation Handoff](docs/agent-implementation-handoff.md)
- [Backend Data Engineering Handoff](docs/backend-data-engineering-handoff.md)
- [Play Integrity Real Device Guide](docs/play-integrity-real-device-guide.md)
- [UI Theme Enhancement](docs/ui-theme-enhancement.md)
- [UI/UX Mini Scope Completion](docs/ui-ux-mini-scope-completion.md)

## Current Project Boundary

This repository is ready for Android agent demonstration, local telemetry upload,
and backend handoff. The next major ownership area is server-side processing:

- final Play Integrity token validation
- telemetry storage
- model/data pipelines
- backend risk scoring
- production API authentication
- dashboard or SOC integration

## Validation Command

Use this before sharing changes:

```powershell
cd C:\Users\ASUS\Desktop\mobile_sec\aegis-agent
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest :app:assembleDebug
```

Expected result:

```text
BUILD SUCCESSFUL
```
