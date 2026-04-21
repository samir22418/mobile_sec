package com.aegis.agent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// =============================================================================
// DeviceReport — immutable snapshot of a device's security posture.
//
// Produced by DeviceScanner and serialized to JSON for upload to the AEGIS
// backend.  All fields use @SerialName so that obfuscated (R8) builds still
// produce a stable JSON schema.
// =============================================================================

/**
 * The Play Integrity verdict ladder.
 *
 * Ordered from strongest to weakest so that callers can do `>=` comparisons:
 *   verdict >= IntegrityVerdict.MEETS_DEVICE_INTEGRITY
 *
 * @see <a href="https://developer.android.com/google/play/integrity/verdicts">
 *      Play Integrity API — verdicts</a>
 */
@Serializable
enum class IntegrityVerdict {
    /** Device passes CTS + strong hardware attestation. */
    @SerialName("MEETS_STRONG_INTEGRITY")
    MEETS_STRONG_INTEGRITY,

    /** Device passes CTS profile match (no hardware attestation required). */
    @SerialName("MEETS_DEVICE_INTEGRITY")
    MEETS_DEVICE_INTEGRITY,

    /** App signed by Play and not sideloaded; device may be rooted/modified. */
    @SerialName("MEETS_BASIC_INTEGRITY")
    MEETS_BASIC_INTEGRITY,

    /** Device / app failed all integrity checks. */
    @SerialName("FAILS")
    FAILS,
}

/**
 * Root detection verdicts — each method is reported independently so the
 * backend can apply its own scoring logic.
 */
@Serializable
data class RootDetectionResult(
    /** True if an `su` binary was found in any of the well-known paths. */
    @SerialName("su_binary_found")
    val suBinaryFound: Boolean,

    /** True if `android.os.Build.TAGS` contains "test-keys". */
    @SerialName("test_keys_found")
    val testKeysFound: Boolean,

    /** True if `/system/app/Superuser.apk` exists on the filesystem. */
    @SerialName("superuser_apk_found")
    val superuserApkFound: Boolean,

    /**
     * Convenience composite: any one of the three methods triggered.
     * Used by the backend risk engine as a single boolean gate.
     */
    @SerialName("is_rooted")
    val isRooted: Boolean = suBinaryFound || testKeysFound || superuserApkFound,
)

/**
 * Full device security posture snapshot produced by [DeviceScanner].
 *
 * @param deviceId          The unique device identifier from [AgentConfig].
 * @param timestampEpochMs  Wall-clock time of the scan (UTC epoch millis).
 * @param rootDetection     Results from all three root-detection methods.
 * @param integrityVerdict  Result of the Play Integrity API call.
 * @param securityPatchDate ISO-8601 date string from Build.VERSION.SECURITY_PATCH
 *                          (e.g. "2024-03-05").
 * @param bootloaderState   Raw string from SystemProperties ro.boot.verifiedbootstate
 *                          (e.g. "green", "yellow", "orange", "red") or "unknown".
 */
@Serializable
data class DeviceReport(
    @SerialName("device_id")
    val deviceId: String,

    @SerialName("timestamp_epoch_ms")
    val timestampEpochMs: Long,

    @SerialName("root_detection")
    val rootDetection: RootDetectionResult,

    @SerialName("integrity_verdict")
    val integrityVerdict: IntegrityVerdict,

    @SerialName("security_patch_date")
    val securityPatchDate: String,

    @SerialName("bootloader_state")
    val bootloaderState: String,
)
