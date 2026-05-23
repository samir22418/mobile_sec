package com.aegis.agent.data.network

import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.IntegrityVerdict
import com.aegis.agent.domain.model.RootDetectionResult
import com.aegis.agent.domain.model.TelemetryPayload
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("TelemetryUploader")
class TelemetryUploaderTest {

    private lateinit var server: MockWebServer
    private lateinit var uploader: TelemetryUploader

    @BeforeEach
    fun setUp() {
        server = MockWebServer()
        server.start()
        uploader = TelemetryUploader(OkHttpClient())
    }

    @AfterEach
    fun tearDown() {
        server.shutdown()
    }

    @Test
    @DisplayName("upload posts telemetry JSON to the POC endpoint")
    fun `upload posts telemetry JSON`() = runTest {
        server.enqueue(MockResponse().setResponseCode(202).setBody("""{"ok":true}"""))

        val payload = payload()
        val result = uploader.upload(
            backendUrl = server.url("/").toString(),
            payload = payload,
        )

        assertTrue(result.isSuccess)
        val request = server.takeRequest()
        assertEquals("/api/v1/telemetry", request.path)
        assertEquals("POST", request.method)
        assertEquals(payload.payloadId, request.getHeader("X-Aegis-Payload-Id"))
        assertEquals(payload.deviceId, request.getHeader("X-Aegis-Device-Id"))
        assertTrue(request.body.readUtf8().contains("\"payload_id\":\"payload-001\""))
    }

    @Test
    @DisplayName("upload returns failure for non-2xx responses")
    fun `upload returns failure for http error`() = runTest {
        server.enqueue(MockResponse().setResponseCode(500).setBody("boom"))

        val result = uploader.upload(
            backendUrl = server.url("/").toString(),
            payload = payload(),
        )

        assertTrue(result.isFailure)
        val error = result.exceptionOrNull()
        assertTrue(error is TelemetryUploadException)
        assertEquals(500, (error as TelemetryUploadException).statusCode)
        assertEquals("boom", error.responseBody)
    }

    @Test
    @DisplayName("telemetryUrl normalizes trailing slash")
    fun `telemetryUrl normalizes trailing slash`() {
        assertEquals(
            "https://example.test/api/v1/telemetry",
            uploader.telemetryUrl("https://example.test/"),
        )
    }

    private fun payload(): TelemetryPayload =
        TelemetryPayload(
            payloadId = "payload-001",
            scanId = 1L,
            deviceId = "device-001",
            createdAtEpochMs = 1_700_000_000_000L,
            deviceReport = DeviceReport(
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
            ),
            appSnapshot = AppSnapshot(
                deviceId = "device-001",
                timestampEpochMs = 1_700_000_000_100L,
                totalAppCount = 0,
                isDelta = false,
                apps = emptyList(),
            ),
        )
}
