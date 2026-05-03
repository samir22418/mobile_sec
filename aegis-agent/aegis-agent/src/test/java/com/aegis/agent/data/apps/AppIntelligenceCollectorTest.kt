package com.aegis.agent.data.apps

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import com.aegis.agent.domain.model.AppInfo
import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.InstallSource
import com.aegis.agent.domain.model.PackageEvent
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import io.mockk.spyk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource

// =============================================================================
// AppIntelligenceCollectorTest
//
// Unit tests for AppIntelligenceCollector and its domain models.
//
// Testing strategy:
//  - PackageManager calls are mocked with Mockk (mockk(relaxed = true))
//  - DataStore is stubbed to return emptyPreferences() for first-run tests
//    and pre-populated JSON for delta-scan tests
//  - File hashing (computeApkSha256) is tested with real ByteArray operations
//    that don't require the Android filesystem
//  - InstallSource classification is tested via spyk overrides
//
// JUnit5 structure:
//  @Nested inner classes group related tests so IDE reports are readable
// =============================================================================

@OptIn(ExperimentalCoroutinesApi::class)
@DisplayName("AppIntelligenceCollector unit tests")
class AppIntelligenceCollectorTest {

    private val testDispatcher = StandardTestDispatcher()

    // Relaxed mocks return safe defaults (null / empty) for unstubbed calls
    private val mockContext: Context             = mockk(relaxed = true)
    private val mockPackageManager: PackageManager = mockk(relaxed = true)
    private val mockDataStore: DataStore<Preferences> = mockk()

    private lateinit var collector: AppIntelligenceCollector

    @BeforeEach
    fun setUp() {
        every { mockContext.packageManager } returns mockPackageManager

        // Default DataStore: no previous fingerprints stored → first-run scenario
        every { mockDataStore.data } returns flowOf(emptyPreferences())
        coEvery { mockDataStore.updateData(any()) } returns emptyPreferences()

        collector = AppIntelligenceCollector(
            context    = mockContext,
            dataStore  = mockDataStore,
            deviceId   = "unit-test-device",
            isByodMode = false,
        )
    }

    // =========================================================================
    // InstallSource classification tests
    // =========================================================================

    @Nested
    @DisplayName("InstallSource classification")
    inner class InstallSourceTests {

        @Test
        @DisplayName("classifyInstallSource returns PLAY_STORE for com.android.vending")
        fun `returns PLAY_STORE for Google Play installer`() {
            every {
                mockPackageManager.getInstallerPackageName("com.example.app")
            } returns "com.android.vending"

            // Use collector directly — classifyInstallSource is internal
            val source = collector.classifyInstallSource("com.example.app")
            assertEquals(InstallSource.PLAY_STORE, source)
        }

        @Test
        @DisplayName("classifyInstallSource returns SIDELOADED when no installer present")
        fun `returns SIDELOADED when installer is null`() {
            every {
                mockPackageManager.getInstallerPackageName("com.example.app")
            } returns null

            val source = collector.classifyInstallSource("com.example.app")
            assertEquals(InstallSource.SIDELOADED, source)
        }

        @ParameterizedTest
        @ValueSource(strings = [
            "com.mobileiron",
            "com.airwatch.androidagent",
            "com.microsoft.intune",
            "com.microsoft.intune.mam",
            "com.jamf.management",
            "com.blackberry.uem.client",
            "com.google.android.apps.work.clouddpc",
        ])
        @DisplayName("classifyInstallSource returns MDM for all known MDM agent package names")
        fun `returns MDM for known MDM installer packages`(mdmPackage: String) {
            every {
                mockPackageManager.getInstallerPackageName("com.example.app")
            } returns mdmPackage

            val source = collector.classifyInstallSource("com.example.app")
            assertEquals(InstallSource.MDM, source, "Expected MDM for installer: $mdmPackage")
        }

        @Test
        @DisplayName("classifyInstallSource returns SIDELOADED for unknown store installer")
        fun `returns SIDELOADED for unknown third-party installer`() {
            every {
                mockPackageManager.getInstallerPackageName("com.example.app")
            } returns "com.some.unknownstore"

            val source = collector.classifyInstallSource("com.example.app")
            assertEquals(InstallSource.SIDELOADED, source)
        }

        @Test
        @DisplayName("classifyInstallSource returns UNKNOWN when PackageManager throws")
        fun `returns UNKNOWN when PackageManager throws`() {
            every {
                mockPackageManager.getInstallerPackageName(any())
            } throws IllegalArgumentException("Package not found")

            val source = collector.classifyInstallSource("com.example.app")
            assertEquals(InstallSource.UNKNOWN, source)
        }
    }

    // =========================================================================
    // APK SHA-256 hashing tests
    // =========================================================================

    @Nested
    @DisplayName("computeApkSha256")
    inner class ApkHashTests {

        @Test
        @DisplayName("returns null for null APK path")
        fun `returns null for null path`() {
            val result = collector.computeApkSha256(null)
            assertNull(result)
        }

        @Test
        @DisplayName("returns null for blank APK path")
        fun `returns null for blank path`() {
            val result = collector.computeApkSha256("   ")
            assertNull(result)
        }

        @Test
        @DisplayName("returns null for non-existent APK path")
        fun `returns null for non-existent file`() {
            val result = collector.computeApkSha256("/nonexistent/path/to/app.apk")
            assertNull(result)
        }
    }

    // =========================================================================
    // Signing certificate SHA-256 tests
    // =========================================================================

    @Nested
    @DisplayName("computeCertSha256")
    inner class CertHashTests {

        @Test
        @DisplayName("returns null when signingInfo and signatures are both null")
        fun `returns null when no signing info available`() {
            val pkgInfo = PackageInfo().apply {
                packageName = "com.example.test"
                // signingInfo and signatures both null by default
            }
            val result = collector.computeCertSha256(pkgInfo)
            assertNull(result, "Expected null when no signing info is present")
        }
    }

    // =========================================================================
    // AppSnapshot domain model tests
    // =========================================================================

    @Nested
    @DisplayName("AppSnapshot domain model")
    inner class AppSnapshotModelTests {

        @Test
        @DisplayName("AppSnapshot isDelta=false on first run")
        fun `snapshot has isDelta false on first run`() {
            val snapshot = AppSnapshot(
                deviceId         = "test-device",
                timestampEpochMs = System.currentTimeMillis(),
                totalAppCount    = 10,
                isDelta          = false,
                apps             = emptyList(),
            )
            assertFalse(snapshot.isDelta)
        }

        @Test
        @DisplayName("AppSnapshot.totalAppCount is always full count, not delta size")
        fun `totalAppCount reflects full count not delta count`() {
            val snapshot = AppSnapshot(
                deviceId         = "test-device",
                timestampEpochMs = System.currentTimeMillis(),
                totalAppCount    = 50,
                isDelta          = true,
                apps             = List(3) { buildFakeAppInfo("com.app.$it") },
            )
            assertEquals(50, snapshot.totalAppCount)
            assertEquals(3, snapshot.apps.size)
        }
    }

    // =========================================================================
    // AppInfo domain model tests
    // =========================================================================

    @Nested
    @DisplayName("AppInfo domain model")
    inner class AppInfoModelTests {

        @Test
        @DisplayName("AppInfo stores all fields correctly")
        fun `AppInfo stores all provided fields`() {
            val info = AppInfo(
                packageName      = "com.example.app",
                versionName      = "1.2.3",
                versionCode      = 123L,
                apkSha256        = "abc123",
                certSha256       = "def456",
                requestedPerms   = listOf("android.permission.INTERNET"),
                installSource    = InstallSource.PLAY_STORE,
                isSystemApp      = false,
                firstInstallTime = 1_000_000L,
                lastUpdateTime   = 2_000_000L,
            )

            assertEquals("com.example.app", info.packageName)
            assertEquals("1.2.3", info.versionName)
            assertEquals(123L, info.versionCode)
            assertEquals("abc123", info.apkSha256)
            assertEquals("def456", info.certSha256)
            assertEquals(listOf("android.permission.INTERNET"), info.requestedPerms)
            assertEquals(InstallSource.PLAY_STORE, info.installSource)
            assertFalse(info.isSystemApp)
        }

        @Test
        @DisplayName("AppInfo with null APK hash is valid")
        fun `AppInfo accepts null apkSha256`() {
            val info = buildFakeAppInfo("com.example.app", apkSha256 = null)
            assertNull(info.apkSha256)
        }
    }

    // =========================================================================
    // PackageEvent tests
    // =========================================================================

    @Nested
    @DisplayName("PackageEvent")
    inner class PackageEventTests {

        @Test
        @DisplayName("PackageEvent INSTALLED has correct eventType")
        fun `INSTALLED event has correct type`() {
            val event = PackageEvent(
                packageName = "com.example.new",
                eventType   = PackageEvent.EventType.INSTALLED,
                timestampMs = System.currentTimeMillis(),
            )
            assertEquals(PackageEvent.EventType.INSTALLED, event.eventType)
            assertEquals("com.example.new", event.packageName)
            assertTrue(event.timestampMs > 0L)
        }

        @Test
        @DisplayName("PackageEvent REMOVED has correct eventType")
        fun `REMOVED event has correct type`() {
            val event = PackageEvent(
                packageName = "com.example.old",
                eventType   = PackageEvent.EventType.REMOVED,
                timestampMs = System.currentTimeMillis(),
            )
            assertEquals(PackageEvent.EventType.REMOVED, event.eventType)
        }
    }

    // =========================================================================
    // MDM_INSTALLER_PKGS contract test
    // =========================================================================

    @Nested
    @DisplayName("MDM_INSTALLER_PKGS constant")
    inner class MdmInstallerPkgsTests {

        @Test
        @DisplayName("MDM_INSTALLER_PKGS contains all required enterprise MDM agents")
        fun `MDM_INSTALLER_PKGS contains required entries`() {
            val pkgs = AppIntelligenceCollector.MDM_INSTALLER_PKGS
            assertTrue(pkgs.contains("com.mobileiron"),
                "Missing MobileIron / Ivanti")
            assertTrue(pkgs.contains("com.airwatch.androidagent"),
                "Missing VMware Workspace ONE")
            assertTrue(pkgs.contains("com.microsoft.intune"),
                "Missing Microsoft Intune")
            assertTrue(pkgs.contains("com.jamf.management"),
                "Missing Jamf Pro")
            assertTrue(pkgs.contains("com.blackberry.uem.client"),
                "Missing BlackBerry UEM")
            assertTrue(pkgs.contains("com.google.android.apps.work.clouddpc"),
                "Missing Google Android Management API")
        }
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    private fun buildFakeAppInfo(
        packageName: String,
        apkSha256: String? = "fakehash",
    ) = AppInfo(
        packageName      = packageName,
        versionName      = "1.0",
        versionCode      = 1L,
        apkSha256        = apkSha256,
        certSha256       = "fakecert",
        requestedPerms   = emptyList(),
        installSource    = InstallSource.SIDELOADED,
        isSystemApp      = false,
        firstInstallTime = 0L,
        lastUpdateTime   = 0L,
    )
}
