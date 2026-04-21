package com.aegis.agent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// =============================================================================
// App Intelligence domain models
//
// Produced by AppIntelligenceCollector and serialized to JSON for upload to the
// AEGIS backend.  All fields use @SerialName so R8-obfuscated names don't break
// the JSON schema agreed with the backend.
// =============================================================================

/**
 * Classifies how a particular APK arrived on the device.
 *
 * Used by the AEGIS risk engine to flag sideloaded or unknown-source apps.
 */
@Serializable
enum class InstallSource {
    /** Installed via the Google Play Store (com.android.vending). */
    @SerialName("PLAY_STORE")
    PLAY_STORE,

    /**
     * Installed by an MDM / Enterprise Mobility Management solution.
     * Identified by recognised installer package names (e.g., com.mobileiron,
     * com.airwatch.androidagent, com.microsoft.intune, etc.).
     */
    @SerialName("MDM")
    MDM,

    /**
     * APK was side-loaded: installed from a file manager, ADB, or an
     * untrusted third-party store.  No recognised installer package was present.
     */
    @SerialName("SIDELOADED")
    SIDELOADED,

    /** Install source could not be determined (e.g., installer package not readable). */
    @SerialName("UNKNOWN")
    UNKNOWN,
}

/**
 * Immutable snapshot of a single installed application's security-relevant metadata.
 *
 * @param packageName       Android package identifier (e.g. "com.example.app").
 * @param versionName       Human-readable version string (e.g. "3.1.2").
 * @param versionCode       Monotonically-increasing integer version code.
 * @param apkSha256         SHA-256 hex digest of the *base* APK file, or `null`
 *                          if the file was not readable (e.g., permission denied).
 * @param certSha256        SHA-256 hex digest of the first signing certificate's
 *                          DER-encoded bytes, or `null` on failure.
 * @param requestedPerms    All permissions listed in the app's AndroidManifest
 *                          (includes NOT-YET-GRANTED runtime permissions).
 * @param installSource     Classified origin of the APK.
 * @param isSystemApp       True if the app is pre-installed in `/system/app` or
 *                          `/system/priv-app`.
 * @param firstInstallTime  Epoch milliseconds when the package was first installed.
 * @param lastUpdateTime    Epoch milliseconds of the most recent update.
 */
@Serializable
data class AppInfo(
    @SerialName("package_name")
    val packageName: String,

    @SerialName("version_name")
    val versionName: String?,

    @SerialName("version_code")
    val versionCode: Long,

    @SerialName("apk_sha256")
    val apkSha256: String?,

    @SerialName("cert_sha256")
    val certSha256: String?,

    @SerialName("requested_permissions")
    val requestedPerms: List<String>,

    @SerialName("install_source")
    val installSource: InstallSource,

    @SerialName("is_system_app")
    val isSystemApp: Boolean,

    @SerialName("first_install_time")
    val firstInstallTime: Long,

    @SerialName("last_update_time")
    val lastUpdateTime: Long,
)

/**
 * A full or delta snapshot of all installed apps on the device.
 *
 * On the **first scan** (no previous state in DataStore) [isDelta] is `false`
 * and [apps] contains every installed package.
 *
 * On **subsequent scans** [isDelta] is `true` and [apps] contains only the
 * packages that were added, removed, or whose metadata changed since the last
 * snapshot — minimising upload bandwidth.
 *
 * @param deviceId          Device identifier (matches [DeviceReport.deviceId]).
 * @param timestampEpochMs  Wall-clock time of the scan (UTC epoch millis).
 * @param totalAppCount     Total number of apps observed in this scan cycle
 *                          (always the full count, even in delta mode).
 * @param isDelta           False on first run; true on subsequent runs where
 *                          only changed entries are included in [apps].
 * @param apps              List of [AppInfo] entries (full or delta).
 */
@Serializable
data class AppSnapshot(
    @SerialName("device_id")
    val deviceId: String,

    @SerialName("timestamp_epoch_ms")
    val timestampEpochMs: Long,

    @SerialName("total_app_count")
    val totalAppCount: Int,

    @SerialName("is_delta")
    val isDelta: Boolean,

    @SerialName("apps")
    val apps: List<AppInfo>,
)

/**
 * Represents a real-time package installation or removal event, emitted by
 * [AppIntelligenceCollector.packageEvents] as a hot [kotlinx.coroutines.flow.Flow].
 *
 * Used by the worker / telemetry layer to trigger an immediate incremental
 * upload without waiting for the next scheduled scan.
 *
 * @param packageName  The package that was installed, updated, or removed.
 * @param eventType    [EventType.INSTALLED] or [EventType.REMOVED].
 * @param timestampMs  Wall-clock epoch millis of the broadcast receipt.
 */
@Serializable
data class PackageEvent(
    @SerialName("package_name")
    val packageName: String,

    @SerialName("event_type")
    val eventType: EventType,

    @SerialName("timestamp_ms")
    val timestampMs: Long,
) {
    /** Type of package change event. */
    @Serializable
    enum class EventType {
        @SerialName("INSTALLED") INSTALLED,
        @SerialName("REMOVED")   REMOVED,
    }
}
