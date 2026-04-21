# AEGIS Agent - Stage 1 Documentation: Device Posture Intelligence

This document provides a comprehensive breakdown of the AEGIS core library, focusing on the **Device Posture Intelligence** module.

---

## 1. 🧭 HIGH-LEVEL OVERVIEW

**What is this project?**
AEGIS (Android Enterprise Guard & Intelligence Security) is a mobile **Endpoint Detection and Response (EDR)** agent library. It is designed to be embedded into Android applications to monitor the security health of the device.

**What problem does it solve?**
Enterprises need to ensure that the devices accessing their data are secure. Standard Android apps are "blind" to whether the device is rooted, running a custom ROM, or if the system integrity has been compromised. AEGIS provides "eyes" into the system state.

**Who would use it?**
-   **Security Teams** in large organizations.
-   **Developers** building high-security apps (banking, internal enterprise tools).
-   **IT Admins** who need to monitor a fleet of employee devices.

**Main Features:**
-   **Multi-prong Root Detection:** Checks for `su` binaries, test-keys, and Superuser management apps.
-   **Hardware-backed Attestation:** Uses Google Play Integrity API for cryptographic proof of device health.
-   **System Telemetry:** Reads security patch levels and bootloader lock states.
-   **Background Sync:** Uses WorkManager to ensure periodic reporting without user intervention.

---

## 2. 🏗 ARCHITECTURE BREAKDOWN

AEGIS follows **Clean Architecture** principles, separating code into layers based on responsibility.

### Layers:
1.  **Data Layer (`agent/data/`)**:
    *   Interacts with the Android OS.
    *   Contains `DeviceScanner`, `RootDetector`, and `IntegrityApiClient`.
    *   Talks to the "outside world" (Filesystem, Google Play Services).
2.  **Domain Layer (`agent/domain/`)**:
    *   Contains the "Business Rules."
    *   Includes Use Cases (like `CollectDeviceTelemetryUseCase`) and pure data models (`DeviceReport`).
    *   *Rule:* This layer doesn't know about Android or specific libraries.
3.  **Presentation/Worker Layer (`agent/data/worker/`)**:
    *   The "entry point" for execution.
    *   `TelemetrySyncWorker` orchestrates the process.
    *   Uses Hilt for Dependency Injection (DI).

### Data Flow:
`TelemetrySyncWorker` (Trigger) → `CollectDeviceTelemetryUseCase` (Logic) → `DeviceScanner` (Orchestrator) → `RootDetector / IntegrityApiClient` (Data).

---

## 3. 🔄 EXECUTION FLOW (VERY IMPORTANT)

### App Initialization
1.  **Host App** calls `AegisSdk.init(context, config)`.
2.  `AegisSdk` saves the configuration to `AgentConfigHolder`.
3.  `WorkManager` is scheduled to run a periodic job (`TelemetrySyncWorker`).

### Telemetry Scan Cycle (Key Action)
1.  **WorkManager** wakes up the `TelemetrySyncWorker` in the background.
2.  The Worker calls `CollectDeviceTelemetryUseCase()`.
3.  The Use Case calls `DeviceScanner.scan()`.
4.  `DeviceScanner` starts multiple parallel checks:
    *   Asks `RootDetector` to look for files (`su`) and build tags.
    *   Asks `IntegrityApiClient` to request a token from Google Play Services.
    *   Reads `Build` version properties via reflection.
5.  All data is packed into a `DeviceReport` object.
6.  The Worker logs the result (and in future stages, will upload it to a server).

---

## 4. 📂 FILE & FOLDER BREAKDOWN

| File | Purpose |
| :--- | :--- |
| `AegisSdk.kt` | The main "Volume Knob" of the SDK. Developers use this to start/stop the agent. |
| `DeviceScanner.kt` | The "Brain" of the scanning process. It gathers info from all sub-systems. |
| `RootDetector.kt` | The "Specialist" that knows how to find signs of hacking (rooting). |
| `IntegrityApiClient.kt` | The "Bridge" to Google's cloud security servers. |
| `DeviceReport.kt` | The "Envelope" containing all security findings, ready to be sent. |
| `ScannerModule.kt` | The "Factory" that tells the app how to create and connect all these classes. |

---

## 5. 🧩 KEY COMPONENTS DEEP DIVE

### `DeviceScanner` (Class)
-   **Job:** Orchestrate the scan.
-   **Primary Method:** `scan()` (returns `DeviceReport`).
-   **Logic:** It manages thread switching (Moving from background threads for files to the Main thread for Google APIs).

### `RootDetector` (Class)
-   **Job:** Detect root access.
-   **Methods:**
    *   `isSuBinaryPresent()`: Scans 7 known folders for the `su` (SuperUser) tool.
    *   `isTestKeysBuild()`: Checks if the OS was signed by developers instead of a manufacturer.
    *   `isSuperuserApkPresent()`: Looks for the management app itself.

---

## 6. 🧠 LOGIC SIMPLIFICATION

### Root Detection Logic (Plain English)
> "To check if a phone is rooted, I will look in the common hiding spots for the `su` tool. Then, I'll check the 'birth certificate' of the Android version (Build Tags) to see if it says 'test'. Finally, I'll check if the 'Superuser' app index file exists."

### Play Integrity Logic (Pseudo-code)
```kotlin
fun checkIntegrity():
    1. Generate a "Nonce" (a unique random ID to prevent replay attacks).
    2. Send Nonce to Google Play Services.
    3. Wait for a signed "Token" from Google.
    4. Decode the Token locally to see labels like "MEETS_DEVICE_INTEGRITY".
    5. Return the result.
```

---

## 7. 🔐 SECURITY ANALYSIS (VERY IMPORTANT)

### Pentester's View:
1.  **Possible Vulnerability:** **Local Bypass.** A highly sophisticated root (like Magisk) can hide the `su` binary and spoof the `Build.TAGS` to show "release-keys".
    *   *Counter-measure:* We use Play Integrity API which uses hardware-backed secrets that are much harder to spoof.
2.  **Insecure API Usage:** The nonce generation is currently local (`deviceId + timestamp`).
    *   *Hardening:* In production, the **Server** should provide the nonce. This prevents a hacker from "recording" a good response and "replaying" it later.
3.  **Reflection:** We use reflection to read `ro.boot.verifiedbootstate`. While effective, some security-hardened ROMs might block reflection or return fake values.

---

## 8. ⚠️ WEAK POINTS & RISKS

-   **Scalability:** Standard `WorkManager` might be delayed by "Doze Mode" on some devices (e.g., Samsung's aggressive battery saving).
-   **Maintainability:** Root detection is a "Cat and Mouse" game. The path list in `RootDetector` will need constant updates as new root methods emerge.
-   **Trust:** Local JWS decoding in `IntegrityApiClient` is **NOT** 100% secure. A hacker can modify the app logic to always return `MEETS_STRONG_INTEGRITY`. **Authoritative verification must happen on the server.**

---

## 9. 🚀 HOW TO RUN THE PROJECT

1.  **Requirements:** Android Studio Jellyfish+, JDK 17.
2.  **Build:** Run `./gradlew assembleDebug`.
3.  **Embed:**
    ```kotlin
    AegisSdk.init(applicationContext, AgentConfig(...))
    ```
4.  **Logs:** Filter Logcat for `tag:AEGIS` or `tag:DeviceScanner`.

---

## 10. 🧪 HOW TO TEST IT

### Manual Testing
-   **Rooted Device:** Run on a device with Magisk. `is_rooted` should be `true`.
-   **Emulator:** Usually has `test-keys`. Check if `testKeysFound` is `true`.
-   **Airplane Mode:** Check if Play Integrity degrades to `FAILS` gracefully without crashing.

---

## 11. 🧱 HOW TO EXTEND THE PROJECT

1.  **App Intelligence:** Add a collector that scans all installed apps for malware signatures (Stage 1.3).
2.  **Network Monitoring:** Detect if a Proxy or VPN is active.
3.  **USB Debugging:** Detect if `adb` is enabled (common entry point for attackers).
4.  **Local Database:** Store scan history so the backend can see "drifts" in security over time.

---

## 12. 🗺 MENTAL MODEL (VERY IMPORTANT)

Imagine AEGIS as a **Security Guard** at a high-security building.
1.  First, he checks your pockets for tools (Root Detection).
2.  Then, he calls your "Headquarters" (Google Play Integrity) to verify your ID badge is real and hasn't been tampered with.
3.  Finally, he writes down the time and your ID number in his logbook (DeviceReport).
4.  He does this walk-around every hour, even if everything seems fine (Background Sync).

---

## 13. 🧑‍🏫 TEACHING MODE

**What is a "Suspending Function"?**
Think of a waiter in a restaurant. If he waits at the table for the food to be cooked, he can't help anyone else (Blocking). If he takes the order and goes to help others until the bell rings (Suspending), he is much more efficient. AEGIS uses `suspend` so we don't freeze the app while checking for root.

**What is Dependency Injection (Hilt)?**
Instead of every class "buying its own tools," we have a "Tool Shed" (`ScannerModule`). When a class needs a `RootDetector`, it just asks for it in the constructor, and Hilt provides it. This makes the code very easy to test because we can "swap" the real tools for "fake" ones during testing.
