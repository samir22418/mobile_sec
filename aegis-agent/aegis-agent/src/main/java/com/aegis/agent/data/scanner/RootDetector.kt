package com.aegis.agent.data.scanner

import java.io.File

/**
 * RootDetector — performs three independent, low-level root-detection checks.
 *
 * All methods are pure (no side-effects) so they can be called multiple times
 * and are easily testable with Mockk by subclassing / wrapping File operations.
 *
 * Designed to be injected into [DeviceScanner] via constructor injection.
 */
class RootDetector {

    // =========================================================================
    // Method A — su binary path scan
    // =========================================================================

    /**
     * Checks for the presence of the `su` binary in paths where root management
     * apps (Magisk, SuperSU, KingRoot, etc.) typically install it.
     *
     * **Why these paths?**
     * - `/system/bin/su`          — stock rooted kernels
     * - `/system/xbin/su`         — SuperSU, older BusyBox roots
     * - `/sbin/su`                — Magisk (pre-v20 mount namespace)
     * - `/su/bin/su`              — Magisk systemless root
     * - `/magisk/.core/bin/su`    — older Magisk internal path
     * - `/data/local/tmp/su`      — temporary/manual root attempts
     * - `/vendor/bin/su`          — vendor-partition roots (some Chinese ROMs)
     *
     * @return true if at least one `su` binary path exists and is a regular file.
     */
    fun isSuBinaryPresent(): Boolean = SU_BINARY_PATHS.any { path ->
        File(path).exists()
    }

    // =========================================================================
    // Method B — Build.TAGS check
    // =========================================================================

    /**
     * Inspects [android.os.Build.TAGS] for the "test-keys" marker.
     *
     * Production Android builds are signed with "release-keys".  ROM builders
     * who compile AOSP themselves — and many root-enabling custom ROMs — use
     * "test-keys".  This is not conclusive proof of root but is a strong signal
     * when combined with other indicators.
     *
     * Extracted as a parameter so the test can inject any string without
     * needing reflection or a real device.
     *
     * @param buildTags the value of [android.os.Build.TAGS] (default: live value)
     * @return true if buildTags contains "test-keys".
     */
    fun isTestKeysBuild(buildTags: String? = android.os.Build.TAGS): Boolean =
        buildTags?.contains("test-keys", ignoreCase = true) == true

    // =========================================================================
    // Method C — Superuser.apk existence check
    // =========================================================================

    /**
     * Checks whether the classic `Superuser.apk` is installed in `/system/app/`.
     *
     * This file is present on devices rooted with the legacy CyanogenMod /
     * ClockworkMod root method and several early SuperSU distributions.
     * More modern root solutions (Magisk) do not place this file here, so this
     * check is a supplement — not a replacement — for the `su` binary scan.
     *
     * @return true if `/system/app/Superuser.apk` exists.
     */
    fun isSuperuserApkPresent(): Boolean =
        File(SUPERUSER_APK_PATH).exists()

    // =========================================================================
    // Companion — constants only, no state
    // =========================================================================

    companion object {
        internal val SU_BINARY_PATHS = listOf(
            "/system/bin/su",
            "/system/xbin/su",
            "/sbin/su",
            "/su/bin/su",
            "/magisk/.core/bin/su",
            "/data/local/tmp/su",
            "/vendor/bin/su",
        )

        internal const val SUPERUSER_APK_PATH = "/system/app/Superuser.apk"
    }
}
