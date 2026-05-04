# AEGIS Agent - Stage 3 Documentation: Log Filter Agent

This document provides a comprehensive breakdown of the **Log Filter Agent** module, which monitors system logs in real-time for security threats.

---

## 1. 🧭 HIGH-LEVEL OVERVIEW

**What is this project?**
The Log Filter Agent is a specialized module within the AEGIS EDR agent. It acts as an active wiretap on the Android device's internal logging system (`logcat`).

**What problem does it solve?**
Many attacks (like SQL injection, brute force attempts, or unauthorized access) write trace evidence to the system log before an app actually crashes or an alarm goes off. By actively scanning logs in real-time, security teams can detect "silent" attacks or suspicious activity that bypasses static app scans.

**Who would use it?**
-   **Security Analysts** looking for real-time Indicators of Compromise (IoCs).
-   **Threat Hunters** analyzing zero-day exploit attempts over fleets of enterprise devices.

**What are the main features?**
-   **Real-time interception:** Taps directly into `logcat` without writing to disk.
-   **Multi-stage Filtering:** Uses blazing-fast tag checks before falling back to heavier Regex checks.
-   **Strict Ephemerality:** Immediately destroys benign logs so employee privacy is protected and memory isn't wasted.
-   **Smart Buffering:** Buffers matched "important" logs and flushes them efficiently (either via a 30-second timer or if 50 logs pile up quickly).

---

## 2. 🏗 ARCHITECTURE BREAKDOWN

The module is built using **Clean Architecture** patterns heavily backed by Kotlin Coroutines.

### Layers:
1.  **Data Source (`LogcatReader.kt`)**: Waiter fetching raw "brief-format" text strings from the OS.
2.  **Filter Engine (`ImportanceFilter.kt`)**: The stateless "brain" deciding if a log is a threat.
3.  **Orchestrator (`LogFilterAgent.kt`)**: The manager holding a thread-safe Queue (Buffer) and running background timers to flush it.
4.  **Domain Models (`ImportantLog.kt`)**: The pure data format `ImportantLog` used for the final output.

### Data Flow step-by-step:
1. `LogcatReader` spawns an OS process and reads the infinite stream of text.
2. The text is parsed into `RawLogLine` (Tag, Level, Message).
3. `LogFilterAgent` passes it to `ImportanceFilter`.
4. If harmless, it goes straight to the garbage collector.
5. If malicious, it gets converted to an `ImportantLog` and placed in the in-memory `ArrayDeque` (Buffer).
6. A background clock ticks every 30 seconds -> The buffer is "flushed" (emptied) into a `SharedFlow`.
7. (Future) The Uploader module observes this Flow and sends the batch to the cloud.

---

## 3. 🔄 EXECUTION FLOW (VERY IMPORTANT)

### When `LogFilterAgent.start()` is called:

1. **Agent** launches Coroutine A (Reader).
2. **Reader** runs `Runtime.getRuntime().exec("logcat -v brief ...")`.
3. **Android OS** starts spitting out log text continuously.
4. For every single line:
   - *Is Tag in our blacklist?* -> YES (Buffer it). NO (Next rule).
   - *Is Level ERROR or WTF?* -> YES (Buffer it). NO (Next rule).
   - *Does the message match threat words ("root", "injection")?* -> YES (Buffer it). NO (Trash it instantly).
5. Concurrently, **Agent** launches Coroutine B (Flusher).
6. **Flusher** goes to sleep for 30 seconds.
7. **Flusher** wakes up, locks the buffer vault (Mutex) so Coroutine A doesn't mess with it.
8. **Flusher** throws away any log older than 10 minutes (TTL).
9. **Flusher** takes the remaining logs, puts them in a box (List), clears the vault.
10. **Flusher** drops the box onto the `filteredLogs` conveyor belt (Flow).

---

## 4. 📂 FILE & FOLDER BREAKDOWN

| File | What it does | Key Functions Explained |
| :--- | :--- | :--- |
| `ImportantLog.kt` | The final JSON structure of a suspicious log. | It exists to enforce a strict contract with the backend server. |
| `ImportanceFilter.kt` | The bouncer at the club. Decides who gets in. | `evaluate()`: Checks the 3 rules in order of CPU-cost (Tag -> Level -> Regex). |
| `LogcatReader.kt` | The wiretap. Spawns the OS command. | `lines()`: Returns a Flow of parsed strings. `parseLine()`: Slices the raw strings. |
| `LogFilterAgent.kt` | The traffic controller. Manages memory and timing. | `start()`: Fires up the readers. `flushBuffer()`: Pushes data out. |
| `LogModule.kt` | Dependency Injection wiring. | `provideLogAgentScope()`: Creates a special sandbox (`SupervisorJob`) so if logs crash, the app doesn't. |

---

## 5. 🧩 KEY COMPONENTS DEEP DIVE

### Important Class: `ImportanceFilter`
*   **What it does:** It is a pure, stateless machine. It takes a raw string, and responds with "Discard" or "Keep because of Rule X".
*   **Why it's smart:** Regular expressions (Regex) are mathematically slow. Checking if the word "SECURITY" equals "SECURITY" is lightning fast. It does the fast checks first, saving massive CPU power on phones.

### Important Function: `LogFilterAgent.flushBuffer()`
*   **What it does:** Safely drains logs from memory to be prepared for upload. 
*   **Why it's smart:** It uses `Mutex.withLock`. Because Android logs arrive on Thread 1 randomly, and the 30-second timer fires on Thread 2 precisely, without a lock, Thread 1 might write while Thread 2 is clearing, intentionally crashing the app.

---

## 6. 🧠 LOGIC SIMPLIFICATION

### The Buffer Logic (Plain English)
> "I have a box that holds exactly 200 sheets of paper (Log lines). If you put a 201st sheet in, I immediately throw the oldest one in the trash. I will empty this box entirely and hand it to the delivery guy every 30 seconds. But, if a massive security crisis happens and the box suddenly gets 50 sheets in 2 seconds... I won't wait. I'll immediately call the delivery guy to come get it right now."

---

## 7. 🔐 SECURITY ANALYSIS (VERY IMPORTANT)

### Pentester's View:
1.  **Vulnerability - Log Flooding (Denial of Service):** An attacker can write thousands of fake "ERROR" level logs specifically designed to match our criteria. This causes the Agent's buffer to constantly flush, rapidly draining the user's battery and maxing out internet bandwidth trying to upload garbage.
    *   *Improvement:* Implement an exponential backoff or "fuse" mechanism on the network uploader when anomaly rates spike.
2.  **Sensitive Data Exposure (PII Leak):** The `Message` field of logs often contains passwords, JWT tokens, or credit cards developers accidentally printed. We forward this verbatim.
    *   *Hardening:* The backend MUST run a sophisticated Data Loss Prevention (DLP) scraper across all incoming logs. The mobile agent shouldn't do this CPU-heavy redaction itself, but it poses a severe liability while in transit.
3.  **Bypass:** If an attacker writes their malicious exploit using `Log.i()` (Info) instead of `Log.e()` (Error), and avoids our specific hardcoded words ("root", "injection", "exploit"), they completely bypass detection.
    *   *Hardening:* The backend must push dynamic, updated threat Regex lists to the agent, similar to how an Antivirus updates virus definitions.

---

## 8. ⚠️ WEAK POINTS & RISKS

-   **Fragility of `logcat` format:** The parser assumes the format is always exactly `E/Tag(pid): msg`. If a custom manufacturer overrides this standard format in their OS variant, our parser `parseLine()` will return Null and the agent goes completely blind.
-   **Doze Mode:** If the phone screen is off and in deep sleep, Android might pause the `logcat` process or pause the 30-second timer Coroutine. We might miss critical logs that happen right before device sleep.

---

## 9. 🚀 HOW TO RUN THE PROJECT

1.  **Dependencies:** Relies heavily on `kotlinx.coroutines` for Flows and Mutexes.
2.  **Run:** Execute `./gradlew assembleDebug`.
3.  **Environment:** No special permissions required in the AndroidManifest. `logcat` access is granted to an app to read *its own* logs automatically. (Note: On modern Android, reading system-wide logs requires ADB root permission `READ_LOGS`).

---

## 10. 🧪 HOW TO TEST IT

### Manual Testing
1.  Launch the app. Find your own app in an emulator.
2.  Use a button that manually triggers: `Log.e("AuthService", "User failed login")`.
3.  Use the `LogFilterAgentTest.kt` unit tests. These are particularly robust because they completely fake the `logcat` process, meaning they run on any OS instantly.

---

## 11. 🧱 HOW TO EXTEND THE PROJECT

1.  **Dynamic Rule Updates:** Have the remote AEGIS backend push down new JSON configurations mapping to new Regex patterns so the app doesn't need an APK update to catch new threats.
2.  **App Filtering:** Filter logs so we only monitor specific process IDs (PIDs) if we suspect a specific app is misbehaving.
3.  **Intelligent Throttling:** If the same exact error ("TLS Handshake Failed") happens 10,000 times a second, compress it into a single entry: `[TLS Handshake Failed x10,000]`.

---

## 12. 🗺 MENTAL MODEL (VERY IMPORTANT)

Imagine a **Gold Panning River**.
1. The river (`LogcatReader.lines()`) is mostly filled with endless useless mud and water (benign system logs). It flows incredibly fast and never stops.
2. The `ImportanceFilter` is the **Pan**. It grabs the river water and shakes it fast. It lets all the water and mud fall through the holes instantly (discard).
3. Sometimes, heavy rocks (ERROR logs) or shiny gold flakes (Threat Regex matches) get caught in the pan.
4. The Miner (`LogFilterAgent`) takes these shiny flakes and drops them into a secure **Leather Pouch** (The `ArrayDeque` buffer).
5. Every 30 minutes, or whenever the pouch gets too heavy, the miner hands the pouch off to the bank carriage (`filteredLogs` flow) for transport.

---

## 13. 🧑‍🏫 TEACHING MODE

**Why use `Mutex` instead of `synchronized()`?**
In Java, you learn `synchronized(lock) { ... }` to prevent two threads from touching a list at the same time. But we are in Kotlin Coroutines. Coroutines aren't attached to threads permanently. If a Coroutine hits a `synchronized` block and has to wait, it permanently freezes the thread underneath it (which might be running 100 other coroutines!). 
`Mutex.withLock` works differently. If it has to wait, it says "Okay thread, I'll go to sleep, go help those other 100 coroutines. Wake me up when the lock is free." It is "non-blocking", saving immense amounts of system resources.

**Why a `Linked List / ArrayDeque`?**
When our buffer hits 200 logs, we want to delete Log #1 when Log #201 arrives. If we used an `ArrayList`, deleting the first item requires shifting the other 199 items over by one space. Doing this 1,000 times a second would melt the CPU. An `ArrayDeque` is circular; it conceptually just moves a pointer forward, meaning adding to the end and removing from the front takes zero math and zero shifting (`O(1)` performance).
