package com.aegis.agent.domain.usecase

import com.aegis.agent.data.network.TelemetryUploadException
import com.aegis.agent.data.network.TelemetryUploader
import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.AgentConfig
import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.IntegrityVerdict
import com.aegis.agent.domain.model.ImportantLog
import com.aegis.agent.domain.model.LogLevel
import com.aegis.agent.domain.model.MatchedRule
import com.aegis.agent.domain.model.RootDetectionResult
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
import com.aegis.agent.domain.model.ScanTrigger
import com.aegis.agent.domain.model.UploadStatus
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("UploadTelemetryUseCase")
class UploadTelemetryUseCaseTest {

    private val json = Json {
        encodeDefaults = true
        ignoreUnknownKeys = true
    }

    private val mockConfigRepository = mockk<ConfigRepository>(relaxed = true)
    private val mockScanResultRepository = mockk<ScanResultRepository>(relaxed = true)
    private val mockTelemetryUploader = mockk<TelemetryUploader>(relaxed = true)

    private val useCase = UploadTelemetryUseCase(
        configRepository = mockConfigRepository,
        scanResultRepository = mockScanResultRepository,
        telemetryUploader = mockTelemetryUploader,
    )

    private val validConfig = AgentConfig(
        backendUrl = "https://aegis.example.com",
        deviceId = "device-001",
        enrollmentToken = "test-token",
    )

    // ---------------------------------------------------------------------------
    // invoke() — dead-letter routing
    // ---------------------------------------------------------------------------

    @Test
    @DisplayName("4xx response dead-letters immediately without retrying")
    fun `4xx response dead-letters immediately`() = kotlinx.coroutines.test.runTest {
        val deviceReport = deviceReport()
        val appSnapshot = appSnapshot()
        val record = scanRecord(
            deviceReportJson = json.encodeToString(deviceReport),
            appSnapshotJson = json.encodeToString(appSnapshot),
            retryCount = 0,
        )
        coEvery { mockConfigRepository.load() } returns validConfig
        coEvery { mockScanResultRepository.getPendingUploads(any()) } returns listOf(record)
        coEvery { mockTelemetryUploader.upload(any(), any()) } returns
            Result.failure(TelemetryUploadException(statusCode = 400, responseBody = "Bad Request"))

        useCase.invoke()

        coVerify(exactly = 1) { mockScanResultRepository.markDeadLetter(record.id, any<Throwable>(), any()) }
        coVerify(exactly = 0) { mockScanResultRepository.markUploadFailed(record.id, any<Throwable>(), any()) }
    }

    @Test
    @DisplayName("5xx response retries when below MAX_UPLOAD_RETRIES")
    fun `5xx response retries when below limit`() = kotlinx.coroutines.test.runTest {
        val deviceReport = deviceReport()
        val appSnapshot = appSnapshot()
        val record = scanRecord(
            deviceReportJson = json.encodeToString(deviceReport),
            appSnapshotJson = json.encodeToString(appSnapshot),
            retryCount = 2,
        )
        coEvery { mockConfigRepository.load() } returns validConfig
        coEvery { mockScanResultRepository.getPendingUploads(any()) } returns listOf(record)
        coEvery { mockTelemetryUploader.upload(any(), any()) } returns
            Result.failure(TelemetryUploadException(statusCode = 503, responseBody = null))

        useCase.invoke()

        coVerify(exactly = 1) { mockScanResultRepository.markUploadFailed(record.id, any<Throwable>(), any()) }
        coVerify(exactly = 0) { mockScanResultRepository.markDeadLetter(record.id, any<Throwable>(), any()) }
    }

    @Test
    @DisplayName("5xx response dead-letters when retry count reaches MAX_UPLOAD_RETRIES")
    fun `5xx response dead-letters when retry limit reached`() = kotlinx.coroutines.test.runTest {
        val deviceReport = deviceReport()
        val appSnapshot = appSnapshot()
        val record = scanRecord(
            deviceReportJson = json.encodeToString(deviceReport),
            appSnapshotJson = json.encodeToString(appSnapshot),
            retryCount = ScanResultRepository.MAX_UPLOAD_RETRIES - 1,
        )
        coEvery { mockConfigRepository.load() } returns validConfig
        coEvery { mockScanResultRepository.getPendingUploads(any()) } returns listOf(record)
        coEvery { mockTelemetryUploader.upload(any(), any()) } returns
            Result.failure(TelemetryUploadException(statusCode = 500, responseBody = null))

        useCase.invoke()

        coVerify(exactly = 1) { mockScanResultRepository.markDeadLetter(record.id, any<Throwable>(), any()) }
        coVerify(exactly = 0) { mockScanResultRepository.markUploadFailed(record.id, any<Throwable>(), any()) }
    }

    @Test
    @DisplayName("payload build failure dead-letters immediately")
    fun `payload build failure dead-letters immediately`() = kotlinx.coroutines.test.runTest {
        val record = scanRecord(deviceReportJson = null, appSnapshotJson = null)
        coEvery { mockConfigRepository.load() } returns validConfig
        coEvery { mockScanResultRepository.getPendingUploads(any()) } returns listOf(record)

        useCase.invoke()

        coVerify(exactly = 1) { mockScanResultRepository.markDeadLetter(record.id, any<Throwable>(), any()) }
        coVerify(exactly = 0) { mockTelemetryUploader.upload(any(), any()) }
    }

    // ---------------------------------------------------------------------------
    // TelemetryUploadException.isRetryable
    // ---------------------------------------------------------------------------

    @Test
    @DisplayName("isRetryable is false for 4xx (except 429)")
    fun `isRetryable is false for 4xx`() {
        assertFalse(TelemetryUploadException(400, null).isRetryable)
        assertFalse(TelemetryUploadException(401, null).isRetryable)
        assertFalse(TelemetryUploadException(403, null).isRetryable)
        assertFalse(TelemetryUploadException(404, null).isRetryable)
        assertFalse(TelemetryUploadException(422, null).isRetryable)
    }

    @Test
    @DisplayName("isRetryable is true for 429 and 5xx")
    fun `isRetryable is true for 429 and 5xx`() {
        assertTrue(TelemetryUploadException(429, null).isRetryable)
        assertTrue(TelemetryUploadException(500, null).isRetryable)
        assertTrue(TelemetryUploadException(502, null).isRetryable)
        assertTrue(TelemetryUploadException(503, null).isRetryable)
    }

    // ---------------------------------------------------------------------------
    // buildPayload — existing tests
    // ---------------------------------------------------------------------------

    @Test
    @DisplayName("buildPayload rebuilds TelemetryPayload from scan record JSON")
    fun `buildPayload rebuilds payload`() {
        val deviceReport = deviceReport()
        val appSnapshot = appSnapshot()
        val record = scanRecord(
            deviceReportJson = json.encodeToString(deviceReport),
            appSnapshotJson = json.encodeToString(appSnapshot),
        )

        val result = useCase.buildPayload(record, "token")

        assertTrue(result.isSuccess)
        val payload = result.getOrThrow()
        assertEquals("payload-001", payload.payloadId)
        assertEquals(7L, payload.scanId)
        assertEquals("device-001", payload.deviceId)
        assertEquals("token", payload.enrollmentToken)
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
            enrollmentToken = "token",
        )

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message?.contains("device report JSON") == true)
    }

    private fun scanRecord(
        deviceReportJson: String?,
        appSnapshotJson: String?,
        retryCount: Int = 0,
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
            retryCount = retryCount,
            lastUploadAttemptAtEpochMs = null,
            lastUploadError = null,
            uploadedAtEpochMs = null,
            deviceId = "device-001",
            isRooted = false,
            integrityVerdict = IntegrityVerdict.NOT_CONFIGURED,
            integrityDetails = "not configured",
            integrityErrorCode = null,
            integrityTokenHashSha256 = null,
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
            integrityVerdict = IntegrityVerdict.NOT_CONFIGURED,
            integrityDetails = "not configured",
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
