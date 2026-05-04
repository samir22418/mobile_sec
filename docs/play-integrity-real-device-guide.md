# Play Integrity Real Device Guide

This document explains why the Integrity part of the scan can fail on an
emulator or real phone, what changed in the project, and how to configure it.

## 1. What was wrong

The sample app was still using:

```kotlin
cloudProjectNumber = 0L
```

That is not a valid Play Integrity setup. On a real device, Google Play
Integrity can reject the request with an invalid cloud project number.

There was also a second problem: the app tried to decode the returned token
locally. That is not correct for production. The Play Integrity token payload is
encrypted and signed, and final verdict decoding must happen on a secure
backend. The Android client can request a token, but it should not decide the
final MEETS_* verdict by decoding that token locally.

## 2. What changed

The project now stores a more honest Integrity state:

- `REQUIRES_BACKEND_VERIFICATION`: token was received successfully
- `NOT_CONFIGURED`: cloud project number is missing or invalid
- `UNAVAILABLE`: Play Store or Google Play services cannot provide Integrity
- `API_ERROR`: network, rate limit, or temporary Google-side error
- `FAILS`: a non-retryable app/device mismatch style failure
- `MEETS_STRONG_INTEGRITY`, `MEETS_DEVICE_INTEGRITY`, `MEETS_BASIC_INTEGRITY`: final backend-decoded verdicts for future backend integration

When a token is received, the app saves:

- `integrity_verdict = REQUIRES_BACKEND_VERIFICATION`
- `integrity_details`
- `integrity_token_hash_sha256`

The token hash is only for correlation. The token itself is not saved.

## 3. How to configure the sample app

Add your Google Cloud project number to the project `local.properties` file:

```properties
AEGIS_CLOUD_PROJECT_NUMBER=123456789012
```

Use the numeric project number, not the project ID string.

Then rebuild and reinstall the app:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :app:assembleDebug --no-daemon
```

The sample app reads that value into:

```kotlin
BuildConfig.AEGIS_CLOUD_PROJECT_NUMBER
```

Then `SampleApp` passes it into:

```kotlin
AgentConfig.cloudProjectNumber
```

## 4. Real device checklist

A real device still needs:

- official Google Play Store installed
- Google Play services installed and updated
- working internet connection
- Play Integrity API enabled for the cloud project
- correct numeric cloud project number
- package/signing setup that matches your Play Console or test setup

If any of these fail, the UI now shows a useful detail instead of only
`FAILS`.

## 5. What you should see

Without a cloud project number:

- Status: `Complete`
- Integrity: `Not configured`
- Headline: `Integrity setup needed`
- Details: tells you to set `AgentConfig.cloudProjectNumber`

With a valid cloud project number and device support:

- Status: `Complete`
- Integrity: `Partially verified`
- Headline: `Integrity partially verified`
- Details: tells you backend verification is still required before full trust

With Play Store or Play services missing/outdated:

- Status: `Complete`
- Integrity: `Unavailable`
- Details: says what device service is missing or outdated

With network/rate-limit/server problems:

- Status: `Complete`
- Integrity: `API error`
- Details: explains retry/network/rate-limit status

## 6. How to inspect logs

Use this while pressing `Run Security Scan`:

```powershell
adb logcat | findstr /i "IntegrityApiClient DeviceScanner TelemetrySyncWorker"
```

Useful log signals:

- `IntegrityApiClient: missing cloudProjectNumber`
- `IntegrityApiClient: token received hash=...`
- `IntegrityApiClient: Play Integrity API is unavailable...`
- `DeviceScanner: scan complete`
- `TelemetrySyncWorker: scan saved`

## 7. Where the new data is stored

Database:

```text
/data/data/com.aegis.agent.sample/databases/aegis_agent.db
```

Table:

```text
scan_records
```

New columns:

- `integrity_details`
- `integrity_error_code`
- `integrity_token_hash_sha256`

The Room database was migrated from version 1 to version 2 so an existing
installed app can keep old scan records.

## 8. Important production note

This project still does not implement backend token verification. That means the
client can prove it received an Integrity token, but it cannot produce the final
trusted verdict by itself.

The correct production flow is:

1. App requests a Play Integrity token.
2. App sends the token to the backend.
3. Backend calls Google's decodeIntegrityToken API.
4. Backend receives the final labels.
5. Backend stores or returns the final `MEETS_*` or `FAILS` verdict.
6. App can display the backend-confirmed result.

References:

- Android classic request flow: https://developer.android.com/google/play/integrity/classic
- Android Integrity verdicts: https://developer.android.com/google/play/integrity/verdicts
- Android error codes: https://developer.android.com/google/play/integrity/reference/com/google/android/play/core/integrity/model/IntegrityErrorCode
