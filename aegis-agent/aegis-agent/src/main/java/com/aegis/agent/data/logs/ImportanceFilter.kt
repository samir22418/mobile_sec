package com.aegis.agent.data.logs

import com.aegis.agent.domain.model.LogLevel
import com.aegis.agent.domain.model.MatchedRule

/**
 * ImportanceFilter — a pure, stateless, fully-testable classifier for raw logcat lines.
 *
 * This class deliberately has **no Android dependencies** so it can be unit-tested
 * on the JVM without Robolectric or an emulator.
 *
 * ## Filter rules (evaluated in priority order)
 * 1. **TAG_KEYWORD:** The log tag contains one of the security-sensitive keywords
 *    defined in [SECURITY_TAG_KEYWORDS] (case-insensitive).
 * 2. **LEVEL_ERROR_OR_ASSERT:** The log level is [LogLevel.ERROR] or [LogLevel.ASSERT].
 * 3. **THREAT_REGEX:** The message body matches any pattern in [THREAT_PATTERNS].
 *
 * If **none** of the three rules match, [evaluate] returns `null` — the caller
 * must discard the line immediately without buffering or storing it anywhere.
 *
 * ## Thread safety
 * All members are immutable after construction. The single instance can safely
 * be shared across coroutines without synchronisation.
 *
 * ## Usage
 * ```kotlin
 * val filter = ImportanceFilter()
 * val result: FilterResult? = filter.evaluate(
 *     tag     = "SecurityManager",
 *     level   = LogLevel.ERROR,
 *     message = "Permission denied for UID 1234"
 * )
 * if (result != null) {
 *     // result.matchedRule tells you WHY this line passed
 *     buffer.add(result)
 * }
 * ```
 */
class ImportanceFilter {

    // Pre-compile all regex patterns once — regex compilation is expensive, and we
    // evaluate these patterns for every logcat line received (potentially thousands
    // per second on active devices).
    private val compiledThreatPatterns: List<Regex> =
        THREAT_PATTERNS.map { it.toRegex(RegexOption.IGNORE_CASE) }

    /**
     * The result of a successful filter evaluation.
     *
     * Returned by [evaluate] when a log line passes at least one filter rule.
     * Contains only the data needed to construct an [ImportantLog] — it is kept
     * lightweight to avoid allocation pressure in the hot path.
     *
     * @param matchedRule  The first rule (in priority order) that passed.
     * @param matchedPattern  The specific pattern string that matched (for
     *                        [MatchedRule.THREAT_REGEX]) or `null` otherwise.
     */
    data class FilterResult(
        val matchedRule: MatchedRule,
        val matchedPattern: String? = null,
    )

    /**
     * Evaluates a single parsed logcat line against all filter rules.
     *
     * Rules are evaluated cheapest-first to minimise CPU cost:
     * 1. Tag substring scan — O(n) string ops on a short string.
     * 2. Level enum equality — O(1).
     * 3. Regex match on message body — O(m×n), only reached if rules 1–2 fail.
     *
     * @param tag     Log tag extracted from the logcat line.
     * @param level   Parsed [LogLevel] of the line.
     * @param message Full message body of the log line.
     * @return A [FilterResult] if the line passes, or `null` if it should be discarded.
     */
    fun evaluate(tag: String, level: LogLevel, message: String): FilterResult? {
        // Rule 1: Security-sensitive tag keyword (fastest check)
        val upperTag = tag.uppercase()
        if (SECURITY_TAG_KEYWORDS.any { keyword -> keyword in upperTag }) {
            return FilterResult(matchedRule = MatchedRule.TAG_KEYWORD)
        }

        // Rule 2: High-severity log level
        if (level == LogLevel.ERROR || level == LogLevel.ASSERT) {
            return FilterResult(matchedRule = MatchedRule.LEVEL_ERROR_OR_ASSERT)
        }

        // Rule 3: Threat-indicator regex match on message body (most expensive)
        for (pattern in compiledThreatPatterns) {
            if (pattern.containsMatchIn(message)) {
                return FilterResult(
                    matchedRule    = MatchedRule.THREAT_REGEX,
                    matchedPattern = pattern.pattern,
                )
            }
        }

        // No rule matched — discard
        return null
    }

    companion object {

        /**
         * Log tag substrings that trigger an automatic pass regardless of log level.
         *
         * All comparisons are case-insensitive (tag is uppercased before matching).
         *
         * Extend this list as new security-relevant subsystems are identified.
         */
        val SECURITY_TAG_KEYWORDS: Set<String> = setOf(
            "SECURITY",
            "AUTH",
            "CRASH",
            "ANOMALY",
            "VIOLATION",
            "PERMISSION",
        )

        /**
         * Threat-indicator regex patterns matched against the log **message body**.
         *
         * Patterns are case-insensitive and use simple substring matching where
         * possible to keep regex complexity low.  Avoid look-ahead/look-behind
         * operators to prevent catastrophic backtracking on large message strings.
         *
         * **Security note:** These patterns are intentionally broad to maximise
         * recall (low false-negative rate) at the cost of precision. False positives
         * are acceptable at the agent level because the backend applies a second,
         * more precise analysis pass before generating alerts.
         */
        val THREAT_PATTERNS: List<String> = listOf(
            """permission\s+denied""",          // e.g. "permission denied" with optional whitespace
            """\broot(?:ed|ing)\b""",            // concrete root/rooted signals; avoids routine "root detection" diagnostics
            """\broot\s+(?:access|shell|user|granted|detected)\b""",
            """\bsu\s+(?:binary|access|shell)\b""",
            """\bsuperuser\b""",
            """\binjection\b""",                // SQL / code injection keywords
            """\bexploit\b""",                  // generic exploit mention
            """brute[\s\-_]?force""",           // "brute force", "brute-force", "bruteforce"
            """failed\s+login""",               // login failure events
            """certificate\s+error""",          // TLS / mTLS problems
            """invalid\s+certificate""",        // alternative cert error phrasing
            """ssl\s+error""",                  // SSL error variants
            """unauthorized\s+access""",        // access control violations
        )
    }
}
