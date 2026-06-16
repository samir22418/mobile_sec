package com.aegis.agent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Play Integrity state saved with a scan.
 *
 * The MEETS_* values are final verdicts that can only be trusted after backend
 * token verification. The client-side API returns an encrypted token, so this
 * app stores REQUIRES_BACKEND_VERIFICATION when a token is received locally.
 */
@Serializable
enum class IntegrityVerdict {
    /** Device passes CTS plus strong hardware attestation after backend decode. */
    @SerialName("MEETS_STRONG_INTEGRITY")
    MEETS_STRONG_INTEGRITY,

    /** Device passes CTS/device integrity after backend decode. */
    @SerialName("MEETS_DEVICE_INTEGRITY")
    MEETS_DEVICE_INTEGRITY,

    /** Device/app meets the basic integrity label after backend decode. */
    @SerialName("MEETS_BASIC_INTEGRITY")
    MEETS_BASIC_INTEGRITY,

    /** Backend-decoded token says the device/app failed all integrity labels. */
    @SerialName("FAILS")
    FAILS,

    /** Client received a token; backend must decode/verify it for final verdict. */
    @SerialName("REQUIRES_BACKEND_VERIFICATION")
    REQUIRES_BACKEND_VERIFICATION,

    /** App did not provide a valid Google Cloud project number. */
    @SerialName("NOT_CONFIGURED")
    NOT_CONFIGURED,

    /** Play Integrity cannot run on this device or Play services stack. */
    @SerialName("UNAVAILABLE")
    UNAVAILABLE,

    /** Play Integrity returned a retryable or non-verdict API error. */
    @SerialName("API_ERROR")
    API_ERROR,
}

/**
 * Raw client-side result from the Play Integrity request.
 *
 * The token is included so the backend can call Google's decodeIntegrityToken
 * API for the authoritative MEETS_* or FAILS verdict.  A SHA-256 hash is also
 * kept for log correlation without re-exposing the full token.
 */
@Serializable
data class IntegrityCheckResult(
    @SerialName("verdict")
    val verdict: IntegrityVerdict,

    @SerialName("details")
    val details: String,

    @SerialName("error_code")
    val errorCode: Int? = null,

    @SerialName("token_hash_sha256")
    val tokenHashSha256: String? = null,

    /** Encrypted Play Integrity token to be verified by the backend. */
    @SerialName("integrity_token")
    val integrityToken: String? = null,

    /** Nonce that was bound into the token request — used for replay protection. */
    @SerialName("integrity_nonce")
    val integrityNonce: String? = null,
)

/**
 * Root detection verdicts. Each method is reported independently so the backend
 * can apply its own scoring logic.
 */
@Serializable
data class RootDetectionResult(
    /** True if an su binary was found in any of the well-known paths. */
    @SerialName("su_binary_found")
    val suBinaryFound: Boolean,

    /** True if android.os.Build.TAGS contains "test-keys". */
    @SerialName("test_keys_found")
    val testKeysFound: Boolean,

    /** True if /system/app/Superuser.apk exists on the filesystem. */
    @SerialName("superuser_apk_found")
    val superuserApkFound: Boolean,

    /** Convenience composite: any one of the three methods triggered. */
    @SerialName("is_rooted")
    val isRooted: Boolean = suBinaryFound || testKeysFound || superuserApkFound,
)

/**
 * Full device security posture snapshot produced by DeviceScanner.
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

    @SerialName("integrity_details")
    val integrityDetails: String? = null,

    @SerialName("integrity_error_code")
    val integrityErrorCode: Int? = null,

    @SerialName("integrity_token_hash_sha256")
    val integrityTokenHashSha256: String? = null,

    /** Raw encrypted token for backend verification. */
    @SerialName("integrity_token")
    val integrityToken: String? = null,

    /** Nonce used when requesting the token — included for replay protection. */
    @SerialName("integrity_nonce")
    val integrityNonce: String? = null,

    @SerialName("security_patch_date")
    val securityPatchDate: String,

    @SerialName("bootloader_state")
    val bootloaderState: String,
)
