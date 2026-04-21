package com.aegis.agent.data.logs

import com.aegis.agent.domain.model.LogLevel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import timber.log.Timber

/**
 * RawLogLine — a single parsed line from logcat output.
 *
 * Logcat's brief format (`logcat -v brief`) produces lines like:
 * ```
 * E/MyTag  (12345): Something went wrong
 * ```
 * Which we parse into the following fields:
 *
 * @param level   Parsed [LogLevel] from the priority letter before '/'.
 * @param tag     Log tag extracted from between '/' and '('.
 * @param message Full message body after ': '.
 * @param raw     The unmodified original line (retained for forensic upload).
 */
data class RawLogLine(
    val level: LogLevel,
    val tag: String,
    val message: String,
    val raw: String,
)

/**
 * LogcatReader — streams live logcat output as a cold [Flow] of [RawLogLine].
 *
 * ## How it works
 * `adb logcat` (and its on-device equivalent via [Runtime.exec]) outputs a
 * continuous stream of lines to `stdout`.  We launch it as a child process and
 * wrap the blocking [BufferedReader.readLine] call inside a `flow {}` builder
 * running on [Dispatchers.IO], which dedicates a thread for the blocking read.
 *
 * ## Cancellation
 * When the collecting coroutine scope is cancelled the `try/finally` in [lines]
 * destroys the child process, which unblocks `readLine()` and terminates the
 * dedicated IO thread.
 *
 * ## Log format: brief
 * We use `-v brief` format for simplicity:
 * ```
 * PRIORITY/TAG(PID): MESSAGE
 * ```
 * Examples:
 * ```
 * E/SecurityManager(1234): Permission denied for UID 9999
 * W/AuthService   (5678): Token expired
 * I/ActivityManager(123): Started activity
 * ```
 *
 * ## Testing without a device
 * In unit tests, replace [lines] with a [kotlinx.coroutines.flow.flowOf] of
 * pre-constructed [RawLogLine] objects — no real logcat process is needed.
 */
class LogcatReader {

    /**
     * Starts reading live logcat output and emits each parsed line downstream.
     *
     * **Format used:** `logcat -v brief -b main,crash,system`
     * - `-v brief` — compact format: `PRIORITY/TAG(PID): MESSAGE`
     * - `-b main,crash,system` — captures the most security-relevant buffers
     *   while excluding `-b events` (binary) and `-b radio` (noisy telephony)
     *
     * The flow is cold — the `logcat` process is NOT started until a coroutine
     * collects this flow.  Multiple collectors would spawn multiple processes;
     * use [kotlinx.coroutines.flow.shareIn] with a single upstream if fan-out
     * is needed.
     *
     * @return A cold [Flow] that emits parsed [RawLogLine] objects indefinitely
     *         until the collecting scope is cancelled or the process exits.
     */
    fun lines(): Flow<RawLogLine> = flow {
        val process = Runtime.getRuntime().exec(
            arrayOf("logcat", "-v", "brief", "-b", "main,crash,system")
        )
        Timber.d("LogcatReader: logcat process started")

        try {
            process.inputStream.bufferedReader().use { reader ->
                var line: String?
                while (reader.readLine().also { line = it } != null) {
                    val parsed = parseLine(line!!)
                    if (parsed != null) emit(parsed)
                }
            }
        } finally {
            // Ensures the logcat child process is cleaned up when the coroutine
            // scope that collects this flow is cancelled.
            process.destroy()
            Timber.d("LogcatReader: logcat process destroyed")
        }
    }.flowOn(Dispatchers.IO) // Block only the IO thread pool, not the caller's dispatcher

    // =========================================================================
    // Line parser
    // =========================================================================

    /**
     * Parses a single logcat `-v brief` line into a [RawLogLine].
     *
     * Brief format: `PRIORITY/TAG(PID): MESSAGE`
     *
     * Lines that do not match this format (e.g., the logcat header banner printed
     * on startup, or continuation lines) are silently ignored by returning `null`.
     *
     * @param line Raw line string from the logcat process stdout.
     * @return Parsed [RawLogLine] or `null` if the line is not a standard log entry.
     */
    internal fun parseLine(line: String): RawLogLine? {
        // Fast reject: minimum viable line "E/T(1): m" is 9 chars
        if (line.length < 9) return null

        // Brief format: "E/SecurityManager(12345): Permission denied"
        //                ^  ^              ^         ^
        //                |  tag            PID       message
        //                priority letter
        val slashIdx = line.indexOf('/')
        if (slashIdx != 1) return null   // priority is always 1 char

        val level = LogLevel.fromLetter(line[0])

        val parenIdx = line.indexOf('(', slashIdx + 1)
        if (parenIdx == -1) return null

        val tag = line.substring(slashIdx + 1, parenIdx).trim()

        // Find ": " separator after the closing paren
        val colonIdx = line.indexOf(": ", parenIdx)
        if (colonIdx == -1) return null

        val message = line.substring(colonIdx + 2)

        return RawLogLine(
            level   = level,
            tag     = tag,
            message = message,
            raw     = line,
        )
    }
}
