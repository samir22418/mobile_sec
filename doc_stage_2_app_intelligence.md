# AEGIS Agent - Stage 2 Documentation: App Intelligence & Inventory

This document provides a comprehensive breakdown of the **App Intelligence Collector** module within the AEGIS core library.

---

## 1. 🧭 HIGH-LEVEL OVERVIEW

**What is this project?**
The App Intelligence Collector is a module within the AEGIS EDR agent. It acts as an application scanner for the Android device.

**What problem does it solve?**
Security teams need to know exactly what software is running on an employee's device. Malicious, outdated, or sideloaded apps pose significant security risks. This module provides a complete inventory of all installed apps, their cryptographic signatures, and their origins.

**Who would use it?**
-   **Security Operations Center (SOC) Analysts** tracking down malware.
-   **IT Administrators** ensuring compliance (e.g., verifying MDM-installed apps).
-   **Threat Hunters** looking for suspicious application sideloading.

**What are the main features?**
-   **Full App Inventory:** Scans all installed packages.
-   **Cryptographic Hashing:** Computes SHA-256 hashes of both the APK file and its signing certificate.
-   **Install Source Tracking:** Determines if an app came from the Play Store, an MDM, or was sideloaded.
-   **Delta Updates:** Saves bandwidth by only reporting apps that have changed since the last scan.
-   **Real-time Monitoring:** Listens for new app installations or removals as they happen.
-   **BYOD Support:** Can filter out system apps on Bring-Your-Own-Device setups for privacy.

---

## 2. 🏗 ARCHITECTURE BREAKDOWN

The module strictly follows **Clean Architecture** to separate concerns:

### Layers:
1.  **Data Layer (`agent/data/apps/`)**:
    *   **Data Source:** OS components like `PackageManager` and `BroadcastReceiver`.
    *   **Local DB:** `DataStore<Preferences>` used to save the last known state.
    *   **Collector:** `AppIntelligenceCollector` handles hashing, filtering, and data aggregation.
2.  **Domain Layer (`agent/domain/`)**:
    *   **Models:** `AppInfo`, `AppSnapshot`, `PackageEvent`. Pure Kotlin classes representing the data.
    *   **Use Cases:** `CollectAppInventoryUseCase`. A single-purpose class that triggers the scan.
3.  **Worker Layer (`agent/data/worker/`)**:
    *   **Controller:** `TelemetrySyncWorker` schedules the background work and calls the Use Case.

### Data Flow (Scan Cycle):
1. `TelemetrySyncWorker` calls `CollectAppInventoryUseCase`.
2. The Use Case triggers `AppIntelligenceCollector.collect()`.
3. The Collector requests massive raw package data from `PackageManager`.
4. The Collector loops through packages, computing hashes (SHA-256) and classifying origins.
5. The Collector asks `DataStore` for the previous scan's "fingerprints".
6. The Collector compares the new data against the old, generating a "Delta" (only what changed).
7. The Collector saves the *new* fingerprints to `DataStore`.
8. The result is serialized to JSON and returned to the Worker.

---

## 3. 🔄 EXECUTION FLOW (VERY IMPORTANT)

### Flow 1: Periodic Background Scan
1. **Trigger:** `WorkManager` wakes up `TelemetrySyncWorker`.
2. **Worker** executes `CollectAppInventoryUseCase()`.
3. **Collector** queries `PackageManager.getInstalledPackages()`.
4. **Collector** iterates through each package:
   - Reads APK bytes and computes SHA-256.
   - Extracts the signing certificate and computes SHA-256.
   - Checks the installer package (Play Store, MDM, or None/Sideloaded).
5. **Collector** fetches the last scan's state from `DataStore`.
6. **Comparison:** If `com.example.app:version123` wasn't in the previous state, it's added to the "Changed Apps" list.
7. **Save:** The new complete list of fingerprints is saved back to `DataStore`.
8. **Return:** An `AppSnapshot` containing the delta is returned to be uploaded.

### Flow 2: Real-time App Installation
1. **Trigger:** User installs a new app. Android OS broadcasts `ACTION_PACKAGE_ADDED`.
2. **Receiver:** `PackageEventReceiver` intercepts the broadcast.
3. **Bridge:** The receiver converts the raw intent into a `PackageEvent(INSTALLED)` object.
4. **Emit:** The event is pushed into a hot Kotlin `Flow`.
5. **Subscribe:** (Future) A listener attached to `packageEvents` reacts immediately, perhaps triggering a fast-tracked upload.

---

## 4. 📂 FILE & FOLDER BREAKDOWN

| File | Purpose | Key Functions |
| :--- | :--- | :--- |
| `domain/model/AppInfo.kt` | Defines the blueprint for app data (`AppInfo`, `AppSnapshot`, `PackageEvent`, `InstallSource`). | Pure data classes, no logic. |
| `data/apps/AppIntelligenceCollector.kt` | The main engine. Collects the inventory, computes hashes, calculates deltas. | `collect()`: Runs the scan. `computeApkSha256()`: Hashes file. `classifyInstallSource()`: Determines origin. |
| `data/apps/PackageEventReceiver.kt` | Translates Android OS broadcasts into Kotlin Streams (Flows). | `packageEvents()`: Sets up the dynamic listener and provides real-time updates. |
| `domain/usecase/CollectAppInventoryUseCase.kt` | A clean wrapper to isolate the Worker from the Data layer. | `invoke()`: Safely executes the collector. |
| `di/AppModule.kt` | Dependency Injection configuration. Tells Hilt how to create the collector and `DataStore`. | `provideAppInventoryDataStore()`: Instantiates the local database. |

---

## 5. 🧩 KEY COMPONENTS DEEP DIVE

### 1. The `AppIntelligenceCollector`
*   **What it does:** It's the heavy lifter. It traverses the filesystem to hash APKs, interrogates package managers, and manages state.
*   **Inputs / Outputs:** Takes nothing -> Outputs an `AppSnapshot`.
*   **Example Usage:** `val snapshot = collector.collect()`

### 2. Delta Diffing with `DataStore`
*   **What it does:** Prevents the app from uploading the same 300 apps every hour. It stores a "Fingerprint" (`packageName:versionCode`) and only reports apps that are new or updated.
*   **Example Usage:** Previous scan had `com.app:1`. Current scan has `com.app:2`. The fingerprint changed, so it gets included in the delta report.

### 3. The `PackageEventReceiver` Flow
*   **What it does:** Uses `callbackFlow` to turn a traditional Android callback (BroadcastReceiver) into a reactive stream that can be observed using Coroutines.

---

## 6. 🧠 LOGIC SIMPLIFICATION

### Delta Diffing Logic (Plain English)
> "First, I'll write down the name and version of every app currently installed. Then, I'll look at the list I saved in my notebook from yesterday. For every app I see today, I'll ask: 'Is this exact version on yesterday's list?'. If no, I'll add it to my 'Changed' report. Finally, I'll erase yesterday's list and save today's list in my notebook for tomorrow."

### Install Source Classification (Pseudo-code)
```kotlin
fun findOrigin(app):
    installer = askAndroidWhoInstalled(app)
    
    if installer is "com.android.vending":
        return PLAY_STORE
    else if installer is in [my list of known MDMs like MobileIron, Intune]:
        return MDM
    else: 
        // Unknown or empty installer means the user downloaded the APK directly
        return SIDELOADED
```

---

## 7. 🔐 SECURITY ANALYSIS (VERY IMPORTANT)

### Pentester's View:
1.  **Vulnerability - Null Hashing Bypasses:** The `computeApkSha256` function degrades gracefully (returns `null`) if it encounters an inaccessible file. A sophisticated attacker might modify file permissions or use deep symbolic links to intentionally trigger this fallback to hide their malicious APK contents.
    *   *Improvement:* Flag `null` hashes as highly suspicious on the backend instead of just treating them as missing data.
2.  **Vulnerability - Installer Spoofing:** The package installer name can be spoofed by a malicious app using specific ADB commands (`adb install -i com.android.vending`) or root privileges.
    *   *Counter-measure:* Do not rely entirely on `InstallSource`. Cross-reference the APK hash with the Play Store on the backend.
3.  **Vulnerability - Signature Check Bypass:** We check the first certificate. Advanced malware sometimes uses "Multiple Signers" (V3 signing blocks) maliciously to hide behind a trusted cert.
    *   *Hardening:* We used the modern API 28+ `SigningInfo` which helps mitigate some rotation tricks, but server-side validation of the full certificate chain is crucial.

---

## 8. ⚠️ WEAK POINTS & RISKS

-   **Performance / Memory:** Hashing 300+ APK files (some over 100MB) takes a lot of CPU and disk I/O. Even though it's chunked (8KB buffer) to prevent OOM (Out Of Memory) errors, it could cause battery drain or device stuttering.
-   **Storage Limits:** Storing fingerprints in `DataStore` as a large JSON string could eventually hit limits if the device has an extreme number of apps.
-   **Security Exception:** If Google continues to restrict the `QUERY_ALL_PACKAGES` permission in future Android versions, this module will go blind.

---

## 9. 🚀 HOW TO RUN THE PROJECT

1.  **Setup:** Ensure you have Android Studio and Gradle configured.
2.  **Dependencies:** Make sure `androidx.datastore:datastore-preferences` is in the `build.gradle.kts` (already added).
3.  **Run:** Execute `./gradlew assembleDebug` to build the agent library.
4.  **Note:** The agent won't run autonomously until embedded in an App that calls `AegisSdk.init()`.

---

## 10. 🧪 HOW TO TEST IT

### Manual Testing Steps
1.  **First Run:** Install a host app containing the SDK. Run the scan. Observe `isDelta = false` and `totalAppCount` matching the size of the `apps` list.
2.  **Second Run:** Run the scan again. Observe `isDelta = true` and the `apps` list is now empty (or small).
3.  **Sideloading Test:** Download an APK from the internet (e.g., via Chrome). Install it. Run the scan. Confirm it shows up in the delta with `installSource = SIDELOADED`.

### Edge Cases
-   Apps with massive split APKs (AABs) - check if hashing is slow.
-   Apps where the developer forgot to sign it properly.
-   Extreme rapid installation of multiple apps (Stress testing the `BroadcastReceiver`).

---

## 11. 🧱 HOW TO EXTEND THE PROJECT

1.  **YARA Rules:** Don't just hash the APK, scan the file contents against known malware YARA signatures locally.
2.  **Suspicious Permissions Alert:** Add local logic to instantly flag (`Result.failure`) if an app requests a dangerous combination (e.g., `READ_SMS` + `INTERNET` + `SYSTEM_ALERT_WINDOW`).
3.  **Live Blocking (Root needed):** Extend the `PackageEventReceiver` to instantly kill/uninstall an app if it matches a blacklist *before* the user opens it.

---

## 12. 🗺 MENTAL MODEL (VERY IMPORTANT)

Imagine the device is an **Office Building** and the Operating System is the **Landlord**.
1.  The `AppIntelligenceCollector` is a **Building Inspector**.
2.  During a full inspection, the Inspector checks every single room (installed app). They check the lock's serial number (APK Hash) and the tenant's ID card (Certificate Hash). They write all this down in a master ledger (DataStore).
3.  Every month thereafter, the Inspector does a quick "Delta" inspection. They just check their ledger. "Room 304 changed their lock? Okay, I'll only write down the new details for Room 304 and report that."
4.  Meanwhile, the `PackageEventReceiver` is the **Security Camera at the Front Door**. The moment a new tenant moves in or out, it instantly sends an alert text message (Flow emission).

---

## 13. 🧑‍🏫 TEACHING MODE

**Why do we use `MessageDigest` and a Buffer?**
Imagine you want to count every word in a 1,000-page book (The APK file).
*   **Bad way:** You try to memorize the entire book all at once, then start counting. Your brain runs out of memory (Out Of Memory Exception).
*   **Good way (Buffer):** You read exactly one page at a time (an 8KB buffer). You add to your running count, forget the page, and turn to the next one. This means calculating the hash of a 1GB game takes the exact same amount of RAM as a 1MB app!

**Why `callbackFlow`?**
Old Android uses "Callbacks" for events. "Hey Android, call me back when an app is installed." This is messy. Modern Kotlin uses "Streams" or "Flows". Think of it like a water pipe. Instead of waiting for a phone call, you connect a pipe. When an app installs, a drop of water flows down the pipe. You can attach filters, diverters, or valves to this pipe very easily using Coroutines. `callbackFlow` is simply the tool we use to convert the old Android "Callback" into a modern Kotlin "Pipe".
