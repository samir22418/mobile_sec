package com.aegis.agent.domain.usecase

import android.content.Context
import com.aegis.agent.data.network.TelemetryUploader
import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.ImportantLog
import com.aegis.agent.domain.model.LogLevel
import com.aegis.agent.domain.model.MatchedRule
import com.aegis.agent.domain.model.RootDetectionResult
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
import com.aegis.agent.domain.model.ScanTrigger
import com.aegis.agent.domain.model.UploadStatus
import io.mockk.mockk
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("UploadTelemetryUseCase")
class UploadTelemetryUseCaseTest {

    private val json = Json {
        encodeDefaults = true
        ignoreUnknownKeys = true
    }

    private val useCase = UploadTelemetryUseCase(
        configRepository = ConfigRepository(mockk<Context>(relaxed = true)),
        scanResultRepository = mockk<ScanResultRepository>(relaxed = true),
        telemetryUploader = mockk<TelemetryUploader>(relaxed = true),
    )

    @Test
    @DisplayName("buildPayload rebuilds TelemetryPayload from scan record JSON")
    fun `buildPayload rebuilds payload`() {
        val deviceReport = deviceReport()
        val appSnapshot = appSnapshot()
        val record = scanRecord(
            deviceReportJson = json.encodeToString(deviceReport),
            appSnapshotJson = json.encodeToString(appSnapshot),
        )

        val result = useCase.buildPayload(record)

        assertTrue(result.isSuccess)
        val payload = result.getOrThrow()
        assertEquals("payload-001", payload.payloadId)
        assertEquals(7L, payload.scanId)
        assertEquals("device-001", payload.deviceId)
        assertEquals(deviceReport, payload.deviceReport)
        assertEquals(appSnapshot, payload.appSnapshot)
        assertEquals(1, payload.importantLogs.size)
        assertEquals("SecurityManager", payload.importantLogs.first().tag)
    }

    @Test
    @DisplayName("buildPayload fails when JSON is missing")
    fun `buildPayload fails when JSON is missing`() {
        val result = useCase.buildPayload(
            record = scanRecord(deviceReportJson = null, appSnapshotJson = "{}"),
        )

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message?.contains("device report JSON") == true)
    }

    private fun scanRecord(
        deviceReportJson: String?,
        appSnapshotJson: String?,
    ): ScanRecord =
        ScanRecord(
            id = 7L,
            status = ScanStatus.SUCCESS,
            trigger = ScanTrigger.MANUAL,
            startedAtEpochMs = 1_700_000_000_000L,
            completedAtEpochMs = 1_700_000_000_500L,
            payloadId = "payload-001",
            payloadCreatedAtEpochMs = 1_700_000_000_500L,
            uploadStatus = UploadStatus.PENDING,
            retryCount = 0,
            lastUploadAttemptAtEpochMs = null,
            lastUploadError = null,
            uploadedAtEpochMs = null,
            deviceId = "device-001",
            isRooted = false,
            securityPatchDate = "2026-05-01",
            bootloaderState = "green",
            totalAppCount = 0,
            changedAppCount = 0,
            isAppDelta = false,
            importantLogCount = 1,
            errorMessage = null,
            deviceReportJson = deviceReportJson,
            appSnapshotJson = appSnapshotJson,
            importantLogsJson = json.encodeToString(listOf(importantLog())),
        )

    private fun deviceReport(): DeviceReport =
        DeviceReport(
            deviceId = "device-001",
            timestampEpochMs = 1_700_000_000_000L,
            rootDetection = RootDetectionResult(
                suBinaryFound = false,
                testKeysFound = false,
                superuserApkFound = false,
            ),
            securityPatchDate = "2026-05-01",
            bootloaderState = "green",
        )

    private fun appSnapshot(): AppSnapshot =
        AppSnapshot(
            deviceId = "device-001",
            timestampEpochMs = 1_700_000_000_100L,
            totalAppCount = 0,
            isDelta = false,
            apps = emptyList(),
        )

    private fun importantLog(): ImportantLog =
        ImportantLog(
            id = 1L,
            timestampEpochMs = 1_700_000_000_300L,
            deviceId = "device-001",
            tag = "SecurityManager",
            level = LogLevel.ERROR,
            message = "permission denied for uid",
            matchedRule = MatchedRule.TAG_KEYWORD,
        )
}
