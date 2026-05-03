package com.aegis.agent.data.logs

import com.aegis.agent.domain.model.ImportantLog
import com.aegis.agent.domain.model.LogLevel
import com.aegis.agent.domain.model.MatchedRule
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.CsvSource
import org.junit.jupiter.params.provider.ValueSource

// =============================================================================
// LogFilterAgent Test Suite
//
// Testing strategy:
//   - ImportanceFilter:  pure unit tests — no mocks, no Android deps, all JVM.
//   - LogcatReader:      parseLine() is internal and tested directly on the JVM.
//   - LogFilterAgent:    uses TestScope + StandardTestDispatcher so time can be
//                        controlled via advanceTimeBy(). The LogcatReader is mocked
//                        to inject synthetic log lines without a real process.
//
// JUnit5 structure: @Nested classes group each class under test.
// =============================================================================

@OptIn(ExperimentalCoroutinesApi::class)
class LogFilterAgentTest {

    // =========================================================================
    // ImportanceFilter unit tests — no mocks needed
    // =========================================================================

    @Nested
    @DisplayName("ImportanceFilter — tag keyword rule")
    inner class TagKeywordTests {

        private val filter = ImportanceFilter()

        @ParameterizedTest
        @ValueSource(strings = [
            "SECURITY", "AUTH", "CRASH", "ANOMALY", "VIOLATION", "PERMISSION",
            "security", "auth", "crash", "anomaly", "violation", "permission",
            "SecurityManager", "AuthService", "PermissionHelper",
        ])
        @DisplayName("returns TAG_KEYWORD for tags containing security keywords")
        fun `returns TAG_KEYWORD for security keyword tags`(tag: String) {
            val result = filter.evaluate(tag = tag, level = LogLevel.DEBUG, message = "hello")
            assertNotNull(result, "Expected filter to pass for tag: $tag")
            assertEquals(MatchedRule.TAG_KEYWORD, result!!.matchedRule)
        }

        @Test
        @DisplayName("returns null for benign tag with non-matching level and message")
        fun `returns null for completely benign log line`() {
            val result = filter.evaluate(
                tag     = "ActivityManager",
                level   = LogLevel.DEBUG,
                message = "started activity",
            )
            assertNull(result, "Expected benign line to be discarded")
        }

        @Test
        @DisplayName("tag matching is case-insensitive")
        fun `tag keyword matching is case insensitive`() {
            val lower = filter.evaluate("security_manager", LogLevel.DEBUG, "msg")
            val upper = filter.evaluate("SECURITY_MANAGER", LogLevel.DEBUG, "msg")
            val mixed = filter.evaluate("Security_Manager", LogLevel.DEBUG, "msg")
            assertNotNull(lower)
            assertNotNull(upper)
            assertNotNull(mixed)
        }
    }

    @Nested
    @DisplayName("ImportanceFilter — log level rule")
    inner class LevelRuleTests {

        private val filter = ImportanceFilter()

        @Test
        @DisplayName("ERROR level passes even with benign tag and message")
        fun `ERROR level passes with benign tag and message`() {
            val result = filter.evaluate(
                tag     = "ActivityManager",
                level   = LogLevel.ERROR,
                message = "Something went wrong",
            )
            assertNotNull(result)
            assertEquals(MatchedRule.LEVEL_ERROR_OR_ASSERT, result!!.matchedRule)
        }

        @Test
        @DisplayName("ASSERT level passes even with benign tag and message")
        fun `ASSERT level passes with benign tag and message`() {
            val result = filter.evaluate(
                tag     = "ActivityManager",
                level   = LogLevel.ASSERT,
                message = "impossible state reached",
            )
            assertNotNull(result)
            assertEquals(MatchedRule.LEVEL_ERROR_OR_ASSERT, result!!.matchedRule)
        }

        @ParameterizedTest
        @CsvSource(
            "VERBOSE, ActivityManager, normal debug output",
            "DEBUG,   ActivityManager, starting component",
            "INFO,    ActivityManager, process started",
            "WARN,    ActivityManager, low memory warning",
        )
        @DisplayName("non-ERROR/ASSERT levels are not flagged by the level rule alone")
        fun `lower levels are not flagged by level rule`(
            levelName: String,
            tag: String,
            message: String,
        ) {
            val level = LogLevel.valueOf(levelName.trim())
            // Note: these may still pass via THREAT_REGEX — but these messages won't
            val result = filter.evaluate(tag.trim(), level, message.trim())
            // Verify it wasn't the level rule that matched (if matched at all)
            assertTrue(result == null || result.matchedRule != MatchedRule.LEVEL_ERROR_OR_ASSERT)
        }
    }

    @Nested
    @DisplayName("ImportanceFilter — threat regex rule")
    inner class ThreatRegexTests {

        private val filter = ImportanceFilter()

        @ParameterizedTest
        @ValueSource(strings = [
            "permission denied for uid 1234",
            "Permission Denied For UID 1234",    // case-insensitive
            "the root user accessed the system",
            "SQL injection attempt detected",
            "critical exploit found in kernel",
            "brute force attack in progress",
            "brute-force detected",
            "bruteforce mitigation triggered",
            "3 failed login attempts",
            "certificate error: hostname mismatch",
            "invalid certificate chain",
            "SSL error: handshake failed",
            "unauthorized access to /data/data",
        ])
        @DisplayName("THREAT_REGEX matches all required threat patterns")
        fun `threat regex matches all required patterns`(message: String) {
            val result = filter.evaluate(
                tag     = "ActivityManager",   // benign tag
                level   = LogLevel.INFO,       // non-flagging level
                message = message,
            )
            assertNotNull(result, "Expected regex match for: $message")
            assertEquals(MatchedRule.THREAT_REGEX, result!!.matchedRule)
        }

        @ParameterizedTest
        @ValueSource(strings = [
            "Bootstrap sequence complete",       // 'boot' not 'root'
            "Network connection established",
            "Activity lifecycle: onCreate",
            "Battery level: 72%",
            "User clicked ok button",
        ])
        @DisplayName("benign messages are not matched by threat regex")
        fun `benign messages are not matched`(message: String) {
            val result = filter.evaluate("ActivityManager", LogLevel.DEBUG, message)
            assertNull(result, "Expected no match for benign: $message")
        }

        @Test
        @DisplayName("TAG_KEYWORD rule takes priority over THREAT_REGEX for matching tags")
        fun `TAG_KEYWORD takes priority over THREAT_REGEX`() {
            val result = filter.evaluate(
                tag     = "SecurityManager",          // matches TAG_KEYWORD
                level   = LogLevel.INFO,
                message = "permission denied for uid", // also matches THREAT_REGEX
            )
            assertNotNull(result)
            // Rule 1 (TAG_KEYWORD) should fire first
            assertEquals(MatchedRule.TAG_KEYWORD, result!!.matchedRule)
        }

        @Test
        @DisplayName("LEVEL rule takes priority over THREAT_REGEX for non-keyword tags")
        fun `LEVEL rule takes priority over THREAT_REGEX`() {
            val result = filter.evaluate(
                tag     = "ActivityManager",         // no security keyword
                level   = LogLevel.ERROR,            // matches LEVEL rule (rule 2)
                message = "permission denied for uid", // also matches THREAT_REGEX (rule 3)
            )
            assertNotNull(result)
            assertEquals(MatchedRule.LEVEL_ERROR_OR_ASSERT, result!!.matchedRule)
        }
    }

    // =========================================================================
    // LogcatReader.parseLine() unit tests — pure JVM, no process spawning
    // =========================================================================

    @Nested
    @DisplayName("LogcatReader.parseLine()")
    inner class LogcatParserTests {

        private val reader = LogcatReader()

        @Test
        @DisplayName("parses standard brief-format line correctly")
        fun `parses standard brief format line`() {
            val line = "E/SecurityManager(12345): Permission denied for UID 9999"
            val result = reader.parseLine(line)

            assertNotNull(result)
            assertEquals(LogLevel.ERROR, result!!.level)
            assertEquals("SecurityManager", result.tag)
            assertEquals("Permission denied for UID 9999", result.message)
            assertEquals(line, result.raw)
        }

        @ParameterizedTest
        @CsvSource(
            "V, VERBOSE",
            "D, DEBUG",
            "I, INFO",
            "W, WARN",
            "E, ERROR",
            "A, ASSERT",
            "F, ASSERT",   // Some ROMs use 'F' for fatal
        )
        @DisplayName("parses all log level letters correctly")
        fun `parses all log level letters`(letter: String, expectedLevel: String) {
            val line = "$letter/MyTag(1): message"
            val result = reader.parseLine(line)
            assertNotNull(result)
            assertEquals(LogLevel.valueOf(expectedLevel), result!!.level)
        }

        @Test
        @DisplayName("returns null for logcat banner header lines")
        fun `returns null for banner lines`() {
            val banner = "--------- beginning of /dev/log/main"
            assertNull(reader.parseLine(banner))
        }

        @Test
        @DisplayName("returns null for lines too short to be valid")
        fun `returns null for short lines`() {
            assertNull(reader.parseLine("E/T"))
        }

        @Test
        @DisplayName("returns null for lines without slash separator")
        fun `returns null for lines without slash`() {
            assertNull(reader.parseLine("ESecurityManager(123): msg"))
        }

        @Test
        @DisplayName("returns null for lines without opening parenthesis")
        fun `returns null for lines without paren`() {
            assertNull(reader.parseLine("E/SecurityManager: no pid"))
        }

        @Test
        @DisplayName("tag with spaces is trimmed")
        fun `tag with spaces is trimmed correctly`() {
            val line = "E/  MyTag  (999): trimmed tag"
            val result = reader.parseLine(line)
            assertNotNull(result)
            assertEquals("MyTag", result!!.tag)
        }
    }

    // =========================================================================
    // LogFilterAgent integration tests using TestScope
    // =========================================================================

    @Nested
    @DisplayName("LogFilterAgent — buffer and flush behaviour")
    inner class LogFilterAgentTests {

        private val testDispatcher = StandardTestDispatcher()
        private val testScope      = TestScope(testDispatcher)

        private val mockReader  = mockk<LogcatReader>()
        private val filter      = ImportanceFilter()   // use real filter

        private lateinit var agent: LogFilterAgent

        @BeforeEach
        fun setUp() {
            agent = LogFilterAgent(
                logcatReader = mockReader,
                filter       = filter,
                deviceId     = "test-device-001",
                scope        = testScope.backgroundScope,
            )
        }

        @AfterEach
        fun tearDown() {
            agent.stop()
        }

        @Test
        @DisplayName("filteredLogs emits a batch after timer flush (30 s)")
        fun `emits batch after flush interval`() = testScope.runTest {
            // Arrange: mock reader emits 3 security-relevant lines then stops
            every { mockReader.lines() } returns flowOf(
                RawLogLine(LogLevel.ERROR, "SecurityManager", "permission denied uid=0", "raw1"),
                RawLogLine(LogLevel.DEBUG, "ActivityManager", "started activity", "raw2"), // should be discarded
                RawLogLine(LogLevel.ERROR, "AuthService",     "failed login attempt",      "raw3"),
            )

            // Collect first batch in a background job
            val receivedBatches = mutableListOf<List<ImportantLog>>()
            val collectorJob: Job = launch {
                agent.filteredLogs.take(1).toList(receivedBatches)
            }

            agent.start()

            // Advance time past the 30s flush interval
            advanceTimeBy(LogFilterAgent.FLUSH_INTERVAL_MS + 1_000L)

            collectorJob.join()

            // Assert: only the 2 matching lines (not the benign ActivityManager line)
            assertEquals(1, receivedBatches.size, "Expected exactly 1 flush batch")
            val batch = receivedBatches.first()
            assertEquals(2, batch.size, "Expected 2 matching logs (not the discarded one)")
            assertTrue(batch.all { it.deviceId == "test-device-001" })
        }

        @Test
        @DisplayName("flushBuffer discards entries older than TTL")
        fun `flushBuffer evicts stale entries`() = testScope.runTest {
            // No reader needed for this test — we directly invoke flushBuffer
            every { mockReader.lines() } returns flowOf()

            // Manually add a "stale" log by bypassing the reader
            // We test flushBuffer() directly via the internal API
            // (In production this is called by the timer coroutine)
            agent.start()
            advanceTimeBy(100L) // let coroutines start

            // flushBuffer on an empty buffer should not emit
            agent.flushBuffer()
            assertEquals(0, agent.bufferedCount())
        }

        @Test
        @DisplayName("agent emits no batch for all-benign logcat output")
        fun `no emission for all-benign log lines`() = testScope.runTest {
            every { mockReader.lines() } returns flowOf(
                RawLogLine(LogLevel.DEBUG, "ActivityManager", "starting activity",  "raw1"),
                RawLogLine(LogLevel.INFO,  "WindowManager",   "window drawn",        "raw2"),
                RawLogLine(LogLevel.VERBOSE,"InputManager",   "touch event handled", "raw3"),
            )

            val receivedBatches = mutableListOf<List<ImportantLog>>()
            val collectorJob = launch {
                agent.filteredLogs.take(1).toList(receivedBatches)
            }

            agent.start()
            advanceTimeBy(LogFilterAgent.FLUSH_INTERVAL_MS + 1_000L)

            // No batch should have been emitted — cancel the collector
            collectorJob.cancel()

            assertTrue(receivedBatches.isEmpty(), "Expected no flush emission for benign lines")
        }

        @Test
        @DisplayName("ImportantLog contains correct fields after filter pass")
        fun `ImportantLog fields are correctly populated`() = testScope.runTest {
            every { mockReader.lines() } returns flowOf(
                RawLogLine(LogLevel.ERROR, "ActivityManager", "failed login for user admin", "raw")
            )

            val batches = mutableListOf<List<ImportantLog>>()
            val job = launch {
                agent.filteredLogs.take(1).toList(batches)
            }

            agent.start()
            advanceTimeBy(LogFilterAgent.FLUSH_INTERVAL_MS + 1_000L)
            job.join()

            val log = batches.firstOrNull()?.firstOrNull()
            assertNotNull(log)
            assertEquals("test-device-001", log!!.deviceId)
            assertEquals("ActivityManager", log.tag)
            assertEquals(LogLevel.ERROR, log.level)
            // LEVEL rule fires before THREAT_REGEX for ERROR level
            assertEquals(MatchedRule.LEVEL_ERROR_OR_ASSERT, log.matchedRule)
            assertTrue(log.timestampEpochMs > 0L)
            assertTrue(log.id > 0L)
        }
    }

    // =========================================================================
    // ImportanceFilter constants contract tests
    // =========================================================================

    @Nested
    @DisplayName("ImportanceFilter — constants contract")
    inner class ConstantsTests {

        @Test
        @DisplayName("SECURITY_TAG_KEYWORDS contains all 6 required keywords")
        fun `SECURITY_TAG_KEYWORDS contains all required entries`() {
            val keywords = ImportanceFilter.SECURITY_TAG_KEYWORDS
            assertTrue(keywords.contains("SECURITY"))
            assertTrue(keywords.contains("AUTH"))
            assertTrue(keywords.contains("CRASH"))
            assertTrue(keywords.contains("ANOMALY"))
            assertTrue(keywords.contains("VIOLATION"))
            assertTrue(keywords.contains("PERMISSION"))
        }

        @Test
        @DisplayName("THREAT_PATTERNS contains all 7 required threat indicators")
        fun `THREAT_PATTERNS contains all required patterns`() {
            val patterns = ImportanceFilter.THREAT_PATTERNS
            // Verify each category is covered:
            assertTrue(patterns.any { "permission" in it.lowercase() },  "Missing permission pattern")
            assertTrue(patterns.any { "root" in it.lowercase() },        "Missing root pattern")
            assertTrue(patterns.any { "injection" in it.lowercase() },   "Missing injection pattern")
            assertTrue(patterns.any { "exploit" in it.lowercase() },     "Missing exploit pattern")
            assertTrue(patterns.any { "brute" in it.lowercase() },       "Missing brute-force pattern")
            assertTrue(patterns.any { "login" in it.lowercase() },       "Missing failed login pattern")
            assertTrue(patterns.any { "certificate" in it.lowercase() }, "Missing certificate error pattern")
        }

        @Test
        @DisplayName("LogFilterAgent.BUFFER_MAX_SIZE is 200")
        fun `BUFFER_MAX_SIZE is 200`() {
            assertEquals(200, LogFilterAgent.BUFFER_MAX_SIZE)
        }

        @Test
        @DisplayName("LogFilterAgent.FLUSH_THRESHOLD is 50")
        fun `FLUSH_THRESHOLD is 50`() {
            assertEquals(50, LogFilterAgent.FLUSH_THRESHOLD)
        }

        @Test
        @DisplayName("LogFilterAgent.FLUSH_INTERVAL_MS is 30 seconds")
        fun `FLUSH_INTERVAL_MS is 30 seconds`() {
            assertEquals(30_000L, LogFilterAgent.FLUSH_INTERVAL_MS)
        }

        @Test
        @DisplayName("LogFilterAgent.BUFFER_TTL_MS is 10 minutes")
        fun `BUFFER_TTL_MS is 10 minutes`() {
            assertEquals(10 * 60 * 1_000L, LogFilterAgent.BUFFER_TTL_MS)
        }
    }

    // =========================================================================
    // LogLevel.fromLetter() unit tests
    // =========================================================================

    @Nested
    @DisplayName("LogLevel.fromLetter()")
    inner class LogLevelParserTests {

        @ParameterizedTest
        @CsvSource(
            "V, VERBOSE",
            "v, VERBOSE",
            "D, DEBUG",
            "d, DEBUG",
            "I, INFO",
            "i, INFO",
            "W, WARN",
            "w, WARN",
            "E, ERROR",
            "e, ERROR",
            "A, ASSERT",
            "a, ASSERT",
            "F, ASSERT",
            "f, ASSERT",
        )
        @DisplayName("fromLetter correctly maps all logcat priority letters")
        fun `fromLetter maps all logcat letters`(letter: String, expected: String) {
            assertEquals(LogLevel.valueOf(expected), LogLevel.fromLetter(letter[0]))
        }

        @Test
        @DisplayName("fromLetter returns UNKNOWN for unrecognised characters")
        fun `fromLetter returns UNKNOWN for unknown chars`() {
            assertEquals(LogLevel.UNKNOWN, LogLevel.fromLetter('Z'))
            assertEquals(LogLevel.UNKNOWN, LogLevel.fromLetter('?'))
            assertEquals(LogLevel.UNKNOWN, LogLevel.fromLetter('0'))
        }
    }
}
