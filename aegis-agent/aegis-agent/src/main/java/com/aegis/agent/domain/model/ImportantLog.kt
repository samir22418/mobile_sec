package com.aegis.agent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// =============================================================================
// LogFilterAgent domain models
//
// All classes are @Serializable so the backend ingestion API can parse them
// without any manual mapping.  @SerialName guards every field against
// R8/ProGuard renaming that would silently break the JSON schema.
// =============================================================================

/**
 * Maps Android's integer log priority constants to a human-readable level enum.
 *
 * Used in [ImportantLog.level] so JSON consumers never receive raw integers.
 *
 * | Android constant | Value | logcat letter |
 * |---|---|---|
 * | [android.util.Log.ERROR] | 6 | E |
 * | [android.util.Log.ASSERT] (wtf) | 7 | A / F |
 *
 * Only ERROR and ASSERT are considered by [ImportanceFilter]; all lower levels
 * are discarded immediately without buffering.
 */
@Serializable
enum class LogLevel {
    @SerialName("VERBOSE") VERBOSE,
    @SerialName("DEBUG")   DEBUG,
    @SerialName("INFO")    INFO,
    @SerialName("WARN")    WARN,
    @SerialName("ERROR")   ERROR,
    @SerialName("ASSERT")  ASSERT,
    @SerialName("UNKNOWN") UNKNOWN;

    companion object {
        /**
         * Parses the single-character log level letter used by logcat output.
         *
         * @param letter Single character from a logcat line (e.g. 'E', 'W', 'A').
         * @return Matching [LogLevel] or [UNKNOWN] if the character is unrecognised.
         */
        fun fromLetter(letter: Char): LogLevel = when (letter.uppercaseChar()) {
            'V' -> VERBOSE
            'D' -> DEBUG
            'I' -> INFO
            'W' -> WARN
            'E' -> ERROR
            'A', 'F' -> ASSERT   // 'A' = assert, 'F' = fatal on some ROM variants
            else      -> UNKNOWN
        }
    }
}

/**
 * Classifies *which* rule caused a log line to pass the [ImportanceFilter].
 *
 * A single line may match multiple rules; we record only the **first** match
 * (highest-priority rule) to keep the payload compact.
 *
 * Priority order:
 * 1. [TAG_KEYWORD] — fastest check, evaluated first.
 * 2. [LEVEL_ERROR_OR_ASSERT] — evaluated second.
 * 3. [THREAT_REGEX] — most expensive check, evaluated last.
 */
@Serializable
enum class MatchedRule {
    /** Log tag contains a security-sensitive keyword (SECURITY, AUTH, etc.). */
    @SerialName("TAG_KEYWORD")           TAG_KEYWORD,

    /** Log level is ERROR ([android.util.Log.ERROR]) or ASSERT ([android.util.Log.wtf]). */
    @SerialName("LEVEL_ERROR_OR_ASSERT") LEVEL_ERROR_OR_ASSERT,

    /** Message body matches a threat-indicator regular expression. */
    @SerialName("THREAT_REGEX")          THREAT_REGEX,
}

/**
 * A single log line that has passed the [ImportanceFilter] and is scheduled
 * for upload to the AEGIS backend.
 *
 * Produced by [LogFilterAgent] and collected into batches for bandwidth-efficient
 * transmission.
 *
 * @param id            Monotonically-increasing in-memory identifier.
 *                      Resets to 0 on process restart — do not rely on it as a
 *                      globally-unique key; use [timestampEpochMs] + [deviceId].
 * @param timestampEpochMs  Wall-clock time the log line was **received** by the
 *                          agent (UTC epoch milliseconds).  Note: this may differ
 *                          from the timestamp embedded in the logcat line itself
 *                          if the device clock has drifted.
 * @param deviceId      AEGIS device identifier (from [AgentConfig.deviceId]).
 * @param tag           Android log tag (the `TAG` string passed to
 *                      [android.util.Log.e] etc.).  Max length 23 characters on
 *                      older Android versions.
 * @param level         Parsed [LogLevel] of the line.
 * @param message       The full message body.  PII should be redacted on the
 *                      backend; the agent forwards it verbatim.
 * @param matchedRule   The [MatchedRule] that caused this line to be retained.
 */
@Serializable
data class ImportantLog(
    @SerialName("id")
    val id: Long,

    @SerialName("timestamp_epoch_ms")
    val timestampEpochMs: Long,

    @SerialName("device_id")
    val deviceId: String,

    @SerialName("tag")
    val tag: String,

    @SerialName("level")
    val level: LogLevel,

    @SerialName("message")
    val message: String,

    @SerialName("matched_rule")
    val matchedRule: MatchedRule,
)
