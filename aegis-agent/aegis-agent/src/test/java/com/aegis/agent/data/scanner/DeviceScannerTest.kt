package com.aegis.agent.data.scanner

import android.content.Context
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.IntegrityCheckResult
import com.aegis.agent.domain.model.IntegrityVerdict
import com.aegis.agent.domain.model.RootDetectionResult
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import io.mockk.spyk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource

@OptIn(ExperimentalCoroutinesApi::class)
@DisplayName("DeviceScanner unit tests")
class DeviceScannerTest {

    private val testDispatcher = StandardTestDispatcher()
    private val mockContext: Context = mockk(relaxed = true)
    private val mockIntegrityClient: IntegrityApiClient = mockk()

    private lateinit var rootDetector: RootDetector
    private lateinit var scanner: DeviceScanner

    @BeforeEach
    fun setUp() {
        rootDetector = RootDetector()
        scanner = spyk(
            DeviceScanner(
                context = mockContext,
                rootDetector = rootDetector,
                integrityApiClient = mockIntegrityClient,
                deviceId = "test-device-001",
                mainDispatcher = testDispatcher,
            ),
            recordPrivateCalls = true,
        )
    }

    @Nested
    @DisplayName("RootDetector")
    inner class RootDetectorTests {

        private lateinit var detector: RootDetector

        @BeforeEach
        fun setUp() {
            detector = RootDetector()
        }

        @Test
        @DisplayName("isSuBinaryPresent() returns false when no su binary exists")
        fun `isSuBinaryPresent returns false on clean device`() {
            assertFalse(detector.isSuBinaryPresent())
        }

        @Test
        @DisplayName("SU_BINARY_PATHS contains seven known root paths")
        fun `SU_BINARY_PATHS has expected paths`() {
            val paths = RootDetector.SU_BINARY_PATHS

            assertEquals(7, paths.size)
            assertTrue(paths.contains("/system/bin/su"))
            assertTrue(paths.contains("/system/xbin/su"))
            assertTrue(paths.contains("/sbin/su"))
            assertTrue(paths.contains("/su/bin/su"))
            assertTrue(paths.contains("/magisk/.core/bin/su"))
            assertTrue(paths.contains("/data/local/tmp/su"))
            assertTrue(paths.contains("/vendor/bin/su"))
        }

        @Test
        @DisplayName("isSuperuserApkPresent() returns false on JVM host")
        fun `isSuperuserApkPresent returns false on JVM host`() {
            assertFalse(detector.isSuperuserApkPresent())
        }

        @ParameterizedTest
        @ValueSource(strings = ["test-keys", "test-keys,dev-keys", "TEST-KEYS"])
        @DisplayName("isTestKeysBuild() returns true for test-key variants")
        fun `isTestKeysBuild returns true for test-key tags`(buildTags: String) {
            assertTrue(detector.isTestKeysBuild(buildTags))
        }

        @ParameterizedTest
        @ValueSource(strings = ["release-keys", "dev-keys", "", "production"])
        @DisplayName("isTestKeysBuild() returns false for non-test-key tags")
        fun `isTestKeysBuild returns false for release tags`(buildTags: String) {
            assertFalse(detector.isTestKeysBuild(buildTags))
        }

        @Test
        @DisplayName("RootDetectionResult.isRooted is true when any method detects root")
        fun `RootDetectionResult isRooted composite is true when any method detects`() {
            assertTrue(
                RootDetectionResult(
                    suBinaryFound = true,
                    testKeysFound = false,
                    superuserApkFound = false,
                ).isRooted
            )
            assertTrue(
                RootDetectionResult(
                    suBinaryFound = false,
                    testKeysFound = true,
                    superuserApkFound = false,
                ).isRooted
            )
            assertTrue(
                RootDetectionResult(
                    suBinaryFound = false,
                    testKeysFound = false,
                    superuserApkFound = true,
                ).isRooted
            )
        }

        @Test
        @DisplayName("RootDetectionResult.isRooted is false when all methods report clean")
        fun `RootDetectionResult isRooted is false when all methods report clean`() {
            val result = RootDetectionResult(
                suBinaryFound = false,
                testKeysFound = false,
                superuserApkFound = false,
            )

            assertFalse(result.isRooted)
        }
    }

    @Nested
    @DisplayName("IntegrityApiClient decoded payload mapping")
    inner class IntegrityApiClientMappingTests {

        private lateinit var client: IntegrityApiClient

        @BeforeEach
        fun setUp() {
            client = IntegrityApiClient(context = mockContext, cloudProjectNumber = 0L)
        }

        @Test
        @DisplayName("mapDecodedPayloadToVerdict returns MEETS_STRONG_INTEGRITY")
        fun `mapDecodedPayloadToVerdict returns MEETS_STRONG_INTEGRITY`() {
            val verdict = client.mapDecodedPayloadToVerdict(
                """{"deviceIntegrity":{"deviceRecognitionVerdict":["MEETS_STRONG_INTEGRITY"]}}"""
            )

            assertEquals(IntegrityVerdict.MEETS_STRONG_INTEGRITY, verdict)
        }

        @Test
        @DisplayName("mapDecodedPayloadToVerdict returns MEETS_DEVICE_INTEGRITY")
        fun `mapDecodedPayloadToVerdict returns MEETS_DEVICE_INTEGRITY`() {
            val verdict = client.mapDecodedPayloadToVerdict(
                """{"deviceIntegrity":{"deviceRecognitionVerdict":["MEETS_DEVICE_INTEGRITY"]}}"""
            )

            assertEquals(IntegrityVerdict.MEETS_DEVICE_INTEGRITY, verdict)
        }

        @Test
        @DisplayName("mapDecodedPayloadToVerdict returns FAILS for no recognized labels")
        fun `mapDecodedPayloadToVerdict returns FAILS for no labels`() {
            val verdict = client.mapDecodedPayloadToVerdict("""{"deviceIntegrity":{}}""")

            assertEquals(IntegrityVerdict.FAILS, verdict)
        }
    }

    @Nested
    @DisplayName("DeviceScanner full scan")
    inner class DeviceScannerScanTests {

        @BeforeEach
        fun setUpScannerMocks() {
            every { scanner.readSecurityPatchDate() } returns "2024-03-05"
            every { scanner.readBootloaderState() } returns "green"
        }

        @Test
        @DisplayName("scan() returns DeviceReport with correct deviceId")
        fun `scan returns DeviceReport with correct deviceId`() = runTest(testDispatcher) {
            coEvery { mockIntegrityClient.queryIntegrity(any()) } returns integrity(IntegrityVerdict.MEETS_DEVICE_INTEGRITY)

            val report: DeviceReport = scanner.scan()

            assertEquals("test-device-001", report.deviceId)
        }

        @Test
        @DisplayName("scan() returns requested integrity verdict")
        fun `scan returns integrity verdict`() = runTest(testDispatcher) {
            coEvery { mockIntegrityClient.queryIntegrity(any()) } returns integrity(IntegrityVerdict.REQUIRES_BACKEND_VERIFICATION)

            val report = scanner.scan()

            assertEquals(IntegrityVerdict.REQUIRES_BACKEND_VERIFICATION, report.integrityVerdict)
            assertEquals("test integrity detail", report.integrityDetails)
        }

        @Test
        @DisplayName("scan() returns API_ERROR when Play Integrity API throws")
        fun `scan returns API_ERROR when integrity client throws`() = runTest(testDispatcher) {
            coEvery {
                mockIntegrityClient.queryIntegrity(any())
            } throws RuntimeException("Network unavailable")

            val report = scanner.scan()

            assertEquals(IntegrityVerdict.API_ERROR, report.integrityVerdict)
            assertTrue(report.integrityDetails?.contains("Network unavailable") == true)
        }

        @Test
        @DisplayName("scan() populates security patch date")
        fun `scan populates securityPatchDate`() = runTest(testDispatcher) {
            coEvery { mockIntegrityClient.queryIntegrity(any()) } returns integrity(IntegrityVerdict.MEETS_BASIC_INTEGRITY)

            val report = scanner.scan()

            assertEquals("2024-03-05", report.securityPatchDate)
        }

        @Test
        @DisplayName("scan() populates bootloader state")
        fun `scan populates bootloaderState`() = runTest(testDispatcher) {
            coEvery { mockIntegrityClient.queryIntegrity(any()) } returns integrity(IntegrityVerdict.MEETS_BASIC_INTEGRITY)

            val report = scanner.scan()

            assertEquals("green", report.bootloaderState)
        }

        @Test
        @DisplayName("scan() returns non-zero timestampEpochMs")
        fun `scan returns positive timestamp`() = runTest(testDispatcher) {
            coEvery { mockIntegrityClient.queryIntegrity(any()) } returns integrity(IntegrityVerdict.MEETS_STRONG_INTEGRITY)

            val report = scanner.scan()

            assertTrue(report.timestampEpochMs > 0L)
        }

        @Test
        @DisplayName("scan() returns rootDetection with all false on clean JVM host")
        fun `scan returns rootDetection all false on JVM host`() = runTest(testDispatcher) {
            coEvery { mockIntegrityClient.queryIntegrity(any()) } returns integrity(IntegrityVerdict.MEETS_STRONG_INTEGRITY)

            val report = scanner.scan()

            assertFalse(report.rootDetection.isRooted)
            assertFalse(report.rootDetection.suBinaryFound)
            assertFalse(report.rootDetection.superuserApkFound)
        }

        @Test
        @DisplayName("scan() DeviceReport is serializable to non-empty JSON string")
        fun `scan result is serializable`() = runTest(testDispatcher) {
            coEvery { mockIntegrityClient.queryIntegrity(any()) } returns integrity(IntegrityVerdict.REQUIRES_BACKEND_VERIFICATION)

            val json = scanner.scanToJson()

            assertNotNull(json)
            assertTrue(json.contains("device_id"))
            assertTrue(json.contains("integrity_verdict"))
            assertTrue(json.contains("integrity_details"))
            assertTrue(json.contains("security_patch_date"))
            assertTrue(json.contains("bootloader_state"))
        }
    }

    @Nested
    @DisplayName("DeviceScanner security patch date")
    inner class SecurityPatchDateTests {

        @Test
        @DisplayName("readSecurityPatchDate returns non-empty value")
        fun `readSecurityPatchDate returns non-empty value`() {
            val plainScanner = DeviceScanner(
                context = mockContext,
                rootDetector = RootDetector(),
                integrityApiClient = mockIntegrityClient,
                deviceId = "test",
            )

            val result = plainScanner.readSecurityPatchDate()

            assertNotNull(result)
            assertTrue(result.isNotEmpty())
        }
    }

    @Nested
    @DisplayName("DeviceScanner bootloader state")
    inner class BootloaderStateTests {

        @Test
        @DisplayName("readBootloaderState returns a non-empty string")
        fun `readBootloaderState returns non-empty string`() {
            val plainScanner = DeviceScanner(
                context = mockContext,
                rootDetector = RootDetector(),
                integrityApiClient = mockIntegrityClient,
                deviceId = "test",
            )

            val result = plainScanner.readBootloaderState()

            assertNotNull(result)
            assertTrue(result.isNotEmpty())
        }

        @Test
        @DisplayName("readBootloaderState returns unknown when reflection fails on JVM")
        fun `readBootloaderState returns unknown on JVM`() {
            val plainScanner = DeviceScanner(
                context = mockContext,
                rootDetector = RootDetector(),
                integrityApiClient = mockIntegrityClient,
                deviceId = "test",
            )

            val result = plainScanner.readBootloaderState()

            assertEquals("unknown", result)
        }
    }

    private fun integrity(verdict: IntegrityVerdict): IntegrityCheckResult =
        IntegrityCheckResult(
            verdict = verdict,
            details = "test integrity detail",
        )
}
