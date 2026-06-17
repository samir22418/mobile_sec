package com.aegis.agent.domain.model

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("TelemetryPayload")
class TelemetryPayloadTest {

    private val json = Json {
        encodeDefaults = true
        ignoreUnknownKeys = true
    }

    @Test
    @DisplayName("stablePayloadId is deterministic for the same scan identity")
    fun `stablePayloadId is deterministic`() {
        val first = TelemetryPayload.stablePayloadId(
            scanId = 42L,
            deviceId = "device-001",
            startedAtEpochMs = 1_700_000_000_000L,
        )
        val second = TelemetryPayload.stablePayloadId(
            scanId = 42L,
            deviceId = "device-001",
            startedAtEpochMs = 1_700_000_000_000L,
        )

        assertEquals(first, second)
    }

    @Test
    @DisplayName("stablePayloadId changes when scan identity changes")
    fun `stablePayloadId changes for a different scan`() {
        val first = TelemetryPayload.stablePayloadId(
            scanId = 42L,
            deviceId = "device-001",
            startedAtEpochMs = 1_700_000_000_000L,
        )
        val second = TelemetryPayload.stablePayloadId(
            scanId = 43L,
            deviceId = "device-001",
            startedAtEpochMs = 1_700_000_000_000L,
        )

        assertNotEquals(first, second)
    }

    @Test
    @DisplayName("create builds the upload contract from config and scan data")
    fun `create builds payload`() {
        val config = AgentConfig(
            backendUrl = "https://api.aegis.test",
            deviceId = "device-001",
            enrollmentToken = "enrollment-token",
        )
        val deviceReport = deviceReport("device-001")
        val appSnapshot = appSnapshot("device-001")
        val importantLogs = listOf(
            ImportantLog(
                id = 1L,
                timestampEpochMs = 1_700_000_000_300L,
                deviceId = "device-001",
                tag = "SecurityManager",
                level = LogLevel.ERROR,
                message = "permission denied for uid",
                matchedRule = MatchedRule.TAG_KEYWORD,
            )
        )

        val payload = TelemetryPayload.create(
            scanId = 7L,
            startedAtEpochMs = 1_700_000_000_000L,
            createdAtEpochMs = 1_700_000_001_000L,
            config = config,
            deviceReport = deviceReport,
            appSnapshot = appSnapshot,
            importantLogs = importantLogs,
        )

        assertEquals(7L, payload.scanId)
        assertEquals("device-001", payload.deviceId)
        assertEquals(deviceReport, payload.deviceReport)
        assertEquals(appSnapshot, payload.appSnapshot)
        assertEquals(importantLogs, payload.importantLogs)
    }

    @Test
    @DisplayName("serialization uses backend-safe snake_case field names")
    fun `serializes with expected field names`() {
        val payload = TelemetryPayload.create(
            scanId = 7L,
            startedAtEpochMs = 1_700_000_000_000L,
            createdAtEpochMs = 1_700_000_001_000L,
            config = AgentConfig(
                backendUrl = "https://api.aegis.test",
                deviceId = "device-001",
                enrollmentToken = "token",
            ),
            deviceReport = deviceReport("device-001"),
            appSnapshot = appSnapshot("device-001"),
        )

        val encoded = json.encodeToString(payload)

        assertTrue(encoded.contains("\"payload_id\""))
        assertTrue(encoded.contains("\"scan_id\""))
        assertTrue(encoded.contains("\"created_at_epoch_ms\""))
        assertTrue(encoded.contains("\"device_report\""))
        assertTrue(encoded.contains("\"app_snapshot\""))
        assertTrue(encoded.contains("\"important_logs\""))
        assertTrue(!encoded.contains("enrollment_token"))
    }

    private fun deviceReport(deviceId: String): DeviceReport =
        DeviceReport(
            deviceId = deviceId,
            timestampEpochMs = 1_700_000_000_100L,
            rootDetection = RootDetectionResult(
                suBinaryFound = false,
                testKeysFound = false,
                superuserApkFound = false,
            ),
            securityPatchDate = "2026-05-01",
            bootloaderState = "green",
        )

    private fun appSnapshot(deviceId: String): AppSnapshot =
        AppSnapshot(
            deviceId = deviceId,
            timestampEpochMs = 1_700_000_000_200L,
            totalAppCount = 0,
            isDelta = false,
            apps = emptyList(),
        )
}
