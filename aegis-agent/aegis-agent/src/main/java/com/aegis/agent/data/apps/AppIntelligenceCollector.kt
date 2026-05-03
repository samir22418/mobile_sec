package com.aegis.agent.data.apps

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.aegis.agent.domain.model.AppInfo
import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.InstallSource
import com.aegis.agent.domain.model.PackageEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import timber.log.Timber
import java.io.File
import java.security.MessageDigest
import javax.inject.Inject
import javax.inject.Named

/**
 * AppIntelligenceCollector — collects a security-focused inventory of all installed
 * applications and tracks real-time install/remove events.
 *
 * ## Responsibilities
 * 1. **Full scan:** enumerate all packages via [PackageManager], filter system apps
 *    in BYOD mode, and compute per-APK security hashes.
 * 2. **Delta diffing:** persist the last-known package fingerprint set in
 *    [DataStore] and emit only *changed* entries on subsequent scans to save
 *    upload bandwidth.
 * 3. **Real-time events:** expose [packageEvents] as a hot [Flow] backed by a
 *    dynamically-registered [PackageEventReceiver].
 *
 * ## Architecture
 * ```
 * TelemetrySyncWorker
 *       │
 *       ▼
 * CollectAppInventoryUseCase
 *       │
 *       ▼
 * AppIntelligenceCollector  ──▶  PackageManager   (enumerate packages)
 *                           ──▶  PackageEventReceiver (real-time flow)
 *                           ──▶  DataStore<Preferences> (delta state)
 *                           ──▶  MessageDigest / SHA-256 (APK + cert hashes)
 * ```
 *
 * ## Thread safety
 * All public `suspend` functions dispatch to [Dispatchers.IO] internally —
 * callers do not need to switch dispatchers.
 *
 * @param context       Application context.
 * @param dataStore     Hilt-provided [DataStore] for delta fingerprint persistence.
 * @param deviceId      Device identifier forwarded into [AppSnapshot].
 * @param isByodMode    When `true`, system apps are excluded from the inventory
 *                      (personal device; only user-installed apps are monitored).
 */
class AppIntelligenceCollector @Inject constructor(
    private val context: Context,
    private val dataStore: DataStore<Preferences>,
    @Named("deviceId")    private val deviceId: String,
    @Named("isByodMode")  private val isByodMode: Boolean,
) {

    // =========================================================================
    // Private constants
    // =========================================================================

    private val packageManager: PackageManager get() = context.packageManager

    private val json = Json {
        prettyPrint      = false
        ignoreUnknownKeys = true
        encodeDefaults   = true
    }

    // DataStore key — stores a JSON-encoded Set<String> of "pkg:versionCode" fingerprints
    private val FINGERPRINTS_KEY = stringPreferencesKey("app_fingerprints_v1")

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * A cold [Flow] that emits a [PackageEvent] whenever a package is installed,
     * updated, or removed on the device.
     *
     * The underlying [BroadcastReceiver] is registered when the flow is collected
     * and unregistered when the collector's coroutine scope is cancelled.
     *
     * Subscribe in a long-lived scope (e.g., WorkManager's coroutine scope or a
     * ViewModel's `viewModelScope`) to receive events continuously.
     *
     * ```kotlin
     * collector.packageEvents
     *     .onEach { event -> handlePackageChange(event) }
     *     .launchIn(applicationScope)
     * ```
     */
    val packageEvents: Flow<PackageEvent> =
        PackageEventReceiver.packageEvents(context)

    /**
     * Performs a full or delta app inventory scan and returns an [AppSnapshot].
     *
     * ### Full scan (first run)
     * When no previous fingerprint exists in [DataStore], all packages matching
     * the [isByodMode] filter are collected and [AppSnapshot.isDelta] is `false`.
     *
     * ### Delta scan (subsequent runs)
     * Only packages whose `"packageName:versionCode"` fingerprint differs from
     * the previously stored set are included in [AppSnapshot.apps].
     * [AppSnapshot.isDelta] is `true` and [AppSnapshot.totalAppCount] always
     * reflects the *current* total, not just the delta size.
     *
     * @return An [AppSnapshot] describing the current or changed app state.
     */
    suspend fun collect(): AppSnapshot = withContext(Dispatchers.IO) {
        Timber.d("AppIntelligenceCollector: starting collection (byod=$isByodMode)")

        val allPackages   = queryInstalledPackages()
        val previousFps   = loadPreviousFingerprints()
        val currentFps    = mutableSetOf<String>()
        val changedApps   = mutableListOf<AppInfo>()

        for (pkgInfo in allPackages) {
            val appInfo    = buildAppInfo(pkgInfo)
            val fingerprint = "${appInfo.packageName}:${appInfo.versionCode}"
            currentFps.add(fingerprint)

            // Include in result if: first scan OR fingerprint is new/changed
            if (previousFps == null || fingerprint !in previousFps) {
                changedApps.add(appInfo)
            }
        }

        // Persist current fingerprints for next scan
        persistFingerprints(currentFps)

        val isDelta = previousFps != null

        Timber.i(
            "AppIntelligenceCollector: scanned ${allPackages.size} apps; " +
            "changed=${changedApps.size} isDelta=$isDelta"
        )

        AppSnapshot(
            deviceId          = deviceId,
            timestampEpochMs  = System.currentTimeMillis(),
            totalAppCount     = allPackages.size,
            isDelta           = isDelta,
            apps              = changedApps,
        )
    }

    /**
     * Serializes the result of [collect] to a compact JSON string.
     *
     * Useful for direct ingestion into the AEGIS upload pipeline without an
     * intermediate deserialization step.
     *
     * @return A compact JSON representation of [AppSnapshot].
     */
    suspend fun collectToJson(): String = json.encodeToString(collect())

    // =========================================================================
    // Package enumeration
    // =========================================================================

    /**
     * Queries [PackageManager] for all installed packages and applies the
     * BYOD filter if [isByodMode] is `true`.
     *
     * On Android 11+ (API 30) the `QUERY_ALL_PACKAGES` permission declared in
     * `AndroidManifest.xml` is required to see packages outside the default
     * visibility list.
     *
     * @return List of [PackageInfo] objects with full flags for signing info
     *         and requested permissions.
     */
    private fun queryInstalledPackages(): List<PackageInfo> {
        val flags = PackageManager.GET_PERMISSIONS or
                    getSigningFlags()

        val allPackages: List<PackageInfo> = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.getInstalledPackages(PackageManager.PackageInfoFlags.of(flags.toLong()))
        } else {
            @Suppress("DEPRECATION")
            packageManager.getInstalledPackages(flags)
        }

        return if (isByodMode) {
            // BYOD: exclude system apps — only report user-installed packages
            allPackages.filter { pkgInfo ->
                pkgInfo.applicationInfo?.flags?.and(ApplicationInfo.FLAG_SYSTEM) == 0
            }.also { filtered ->
                Timber.d(
                    "AppIntelligenceCollector: BYOD filter applied — " +
                    "${allPackages.size} total → ${filtered.size} user apps"
                )
            }
        } else {
            // Fully-managed (MDM): report everything including system apps
            allPackages
        }
    }

    /** Returns the correct signing flags for the running API level. */
    @Suppress("DEPRECATION")
    private fun getSigningFlags(): Int =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            PackageManager.GET_SIGNING_CERTIFICATES
        } else {
            PackageManager.GET_SIGNATURES
        }

    // =========================================================================
    // AppInfo construction
    // =========================================================================

    /**
     * Builds a fully-populated [AppInfo] from a [PackageInfo] entry.
     *
     * Hash computations are best-effort — if the APK file is inaccessible or
     * the certificate is missing the corresponding field is `null` rather than
     * throwing.
     *
     * @param pkgInfo The [PackageInfo] returned by [PackageManager].
     * @return Populated [AppInfo] instance.
     */
    private fun buildAppInfo(pkgInfo: PackageInfo): AppInfo {
        val appInfo = pkgInfo.applicationInfo

        return AppInfo(
            packageName      = pkgInfo.packageName,
            versionName      = pkgInfo.versionName,
            versionCode      = getVersionCode(pkgInfo),
            apkSha256        = computeApkSha256(appInfo?.publicSourceDir),
            certSha256       = computeCertSha256(pkgInfo),
            requestedPerms   = pkgInfo.requestedPermissions?.toList() ?: emptyList(),
            installSource    = classifyInstallSource(pkgInfo.packageName),
            isSystemApp      = appInfo?.flags?.and(ApplicationInfo.FLAG_SYSTEM) != 0,
            firstInstallTime = pkgInfo.firstInstallTime,
            lastUpdateTime   = pkgInfo.lastUpdateTime,
        )
    }

    /** Extracts the version code in a backward-compatible way (API 26+). */
    @Suppress("DEPRECATION")
    private fun getVersionCode(pkgInfo: PackageInfo): Long =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            pkgInfo.longVersionCode
        } else {
            pkgInfo.versionCode.toLong()
        }

    // =========================================================================
    // APK SHA-256 hash
    // =========================================================================

    /**
     * Computes the SHA-256 digest of the base APK file.
     *
     * The file is streamed in 8 KB chunks so memory usage is bounded regardless
     * of APK size.  Returns `null` if the path is blank or the file is
     * unreadable (e.g., permission denied for `/data/app/` entries).
     *
     * @param apkPath Absolute path to the base APK (from [ApplicationInfo.publicSourceDir]).
     * @return Lowercase hex-encoded SHA-256 digest, or `null` on failure.
     */
    internal fun computeApkSha256(apkPath: String?): String? {
        if (apkPath.isNullOrBlank()) return null
        return try {
            val digest = MessageDigest.getInstance("SHA-256")
            File(apkPath).inputStream().buffered(BUFFER_SIZE).use { stream ->
                val buffer = ByteArray(BUFFER_SIZE)
                var read: Int
                while (stream.read(buffer).also { read = it } != -1) {
                    digest.update(buffer, 0, read)
                }
            }
            digest.digest().toHexString()
        } catch (e: Exception) {
            Timber.w(e, "AppIntelligenceCollector: could not hash APK at $apkPath")
            null
        }
    }

    // =========================================================================
    // Signing certificate SHA-256 hash
    // =========================================================================

    /**
     * Extracts the SHA-256 fingerprint of the first signing certificate.
     *
     * On API 28+ uses [android.content.pm.PackageInfo.signingInfo] with
     * `GET_SIGNING_CERTIFICATES`.  Falls back to the deprecated
     * [android.content.pm.PackageInfo.signatures] on older APIs.
     *
     * @param pkgInfo The [PackageInfo] (must have been queried with signing flags).
     * @return Lowercase hex-encoded SHA-256 of the DER certificate, or `null`.
     */
    @Suppress("DEPRECATION")
    internal fun computeCertSha256(pkgInfo: PackageInfo): String? {
        return try {
            val certBytes: ByteArray? =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    // Prefer the new SigningInfo API (handles key rotation)
                    pkgInfo.signingInfo
                        ?.apkContentsSigners
                        ?.firstOrNull()
                        ?.toByteArray()
                } else {
                    pkgInfo.signatures?.firstOrNull()?.toByteArray()
                }

            certBytes?.let { bytes ->
                MessageDigest.getInstance("SHA-256")
                    .digest(bytes)
                    .toHexString()
            }
        } catch (e: Exception) {
            Timber.w(e, "AppIntelligenceCollector: could not read cert for ${pkgInfo.packageName}")
            null
        }
    }

    // =========================================================================
    // Install source classification
    // =========================================================================

    /**
     * Classifies the installation origin of a package as [InstallSource].
     *
     * Logic:
     * - If the installer package is `com.android.vending` → [InstallSource.PLAY_STORE]
     * - If the installer is a known MDM agent → [InstallSource.MDM]
     * - If there is no installer or it is unrecognised → [InstallSource.SIDELOADED]
     * - If [PackageManager] throws → [InstallSource.UNKNOWN]
     *
     * On API 30+ [PackageManager.getInstallSourceInfo] is preferred because it
     * provides the *initiating* installer, which is more reliable than the
     * deprecated [PackageManager.getInstallerPackageName].
     *
     * @param packageName The package name to classify.
     * @return [InstallSource] enum value.
     */
    internal fun classifyInstallSource(packageName: String): InstallSource {
        return try {
            val installerPkg: String? =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    packageManager.getInstallSourceInfo(packageName).initiatingPackageName
                } else {
                    @Suppress("DEPRECATION")
                    packageManager.getInstallerPackageName(packageName)
                }

            when {
                installerPkg == null              -> InstallSource.SIDELOADED
                installerPkg in PLAY_STORE_PKGS   -> InstallSource.PLAY_STORE
                installerPkg in MDM_INSTALLER_PKGS -> InstallSource.MDM
                else                              -> InstallSource.SIDELOADED
            }
        } catch (e: Exception) {
            Timber.w(e, "AppIntelligenceCollector: could not determine install source for $packageName")
            InstallSource.UNKNOWN
        }
    }

    // =========================================================================
    // DataStore — delta fingerprint persistence
    // =========================================================================

    /**
     * Loads the previously-persisted set of package fingerprints from [DataStore].
     *
     * Returns `null` on the first run (no stored value) — callers treat `null`
     * as "no previous state, emit full scan."
     *
     * Each fingerprint is the string `"packageName:versionCode"`.
     *
     * @return Immutable [Set] of fingerprint strings, or `null` if none stored.
     */
    private suspend fun loadPreviousFingerprints(): Set<String>? {
        return try {
            val prefs = dataStore.data.first()
            val raw = prefs[FINGERPRINTS_KEY]
            if (raw.isNullOrBlank()) {
                null
            } else {
                json.decodeFromString<Set<String>>(raw)
            }
        } catch (e: Exception) {
            Timber.w(e, "AppIntelligenceCollector: could not load previous fingerprints; treating as first run")
            null
        }
    }

    /**
     * Persists a new set of package fingerprints to [DataStore].
     *
     * Called after every successful scan so the next invocation can compute
     * a delta.  Uses [DataStore.edit] which is transactional and crash-safe.
     *
     * @param fingerprints The current set of `"packageName:versionCode"` strings.
     */
    private suspend fun persistFingerprints(fingerprints: Set<String>) {
        try {
            dataStore.edit { prefs ->
                prefs[FINGERPRINTS_KEY] = json.encodeToString(fingerprints)
            }
            Timber.d("AppIntelligenceCollector: persisted ${fingerprints.size} fingerprints")
        } catch (e: Exception) {
            Timber.w(e, "AppIntelligenceCollector: could not persist fingerprints")
        }
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    /** Converts a byte array to a lowercase hex string. */
    private fun ByteArray.toHexString(): String =
        joinToString("") { "%02x".format(it) }

    companion object {
        private const val BUFFER_SIZE = 8 * 1024 // 8 KB streaming buffer

        /** Package names recognised as the Google Play Store installer. */
        internal val PLAY_STORE_PKGS = setOf(
            "com.android.vending",          // Standard Play Store
            "com.google.android.feedback",  // Play on some Samsung devices
        )

        /**
         * Package names of well-known MDM agents.
         *
         * This list is intentionally conservative — only widely-deployed agents.
         * Extend as new MDM vendors are supported by the AEGIS backend.
         */
        internal val MDM_INSTALLER_PKGS = setOf(
            "com.mobileiron",                    // MobileIron / Ivanti
            "com.airwatch.androidagent",         // VMware Workspace ONE
            "com.microsoft.intune",              // Microsoft Intune
            "com.microsoft.intune.mam",          // Intune MAM
            "com.jamf.management",               // Jamf Pro
            "com.blackberry.uem.client",         // BlackBerry UEM
            "com.soti.mobicontrol",              // SOTI MobiControl
            "com.cisco.secureclient.anydeskless", // Cisco Meraki MDM
            "com.google.android.apps.work.clouddpc", // Android Management API / Google MDM
        )
    }
}
