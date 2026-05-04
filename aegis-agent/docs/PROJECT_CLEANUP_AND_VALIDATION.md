# Project Cleanup And Validation

## Removed Runtime/Generated Folders

The following folders were removed locally because they are generated or runtime-only and should not be part of the committed project:

```text
aegis-agent/build
aegis-agent/.gradle
aegis-agent/app/build
aegis-agent/aegis-agent/build
aegis-agent/poc-server-data
```

These folders can be recreated by Gradle, Android Studio, or the POC server when needed.

## Kept

The following were intentionally kept:

- source code
- Gradle files
- documentation
- POC server source
- telemetry schema
- `local.properties` locally, because it is useful for running the sample app and already ignored

## Validation

Commands run after cleanup:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :aegis-agent:testDebugUnitTest :app:assembleDebug
```

Result:

```text
BUILD SUCCESSFUL
```

POC server smoke:

```text
healthOk=True
accepted=True
payloadId=smoke-payload
jsonlLines=1
```

Emulator UI smoke:

- app installed
- app launched
- main activity resumed
- Run Security Scan visible
- Settings visible
- Share Analyst Brief visible
- Dark/Light mode toggle visible
- Settings screen opened
- Backend URL and Enrollment fields visible

