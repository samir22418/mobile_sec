package com.aegis.agent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

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

    @SerialName("security_patch_date")
    val securityPatchDate: String,

    @SerialName("bootloader_state")
    val bootloaderState: String,
)
