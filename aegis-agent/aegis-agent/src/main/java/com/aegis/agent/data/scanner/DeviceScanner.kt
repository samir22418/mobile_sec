package com.aegis.agent.data.scanner

import android.content.Context
import android.os.Build
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.RootDetectionResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import timber.log.Timber
import java.lang.reflect.Method
import javax.inject.Inject
import javax.inject.Named

/**
 * DeviceScanner — orchestrates a full device security posture scan and returns
 * the result as a [DeviceReport].
 *
 * ## Architecture
 * ```
 * TelemetrySyncWorker
 *       │
 *       ▼
 * CollectDeviceTelemetryUseCase
 *       │
 *       ▼
 * DeviceScanner   ──▶  RootDetector
 *                 ──▶  Build / SystemProperties
 * ```
 */
class DeviceScanner @Inject constructor(
    private val context: Context,
    private val rootDetector: RootDetector,
    @Named("deviceId") private val deviceId: String,
) {

    private val json = Json {
        prettyPrint = false
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    suspend fun scan(): DeviceReport = withContext(Dispatchers.IO) {
        Timber.d("DeviceScanner: starting posture scan for device=$deviceId")

        val rootResult = detectRoot()
        val patchDate  = readSecurityPatchDate()
        val bootloader = readBootloaderState()

        DeviceReport(
            deviceId          = deviceId,
            timestampEpochMs  = System.currentTimeMillis(),
            rootDetection     = rootResult,
            securityPatchDate = patchDate,
            bootloaderState   = bootloader,
        ).also {
            Timber.i(
                "DeviceScanner: scan complete — rooted=${it.rootDetection.isRooted} " +
                "patch=${it.securityPatchDate} bootloader=${it.bootloaderState}"
            )
        }
    }

    suspend fun scanToJson(): String = json.encodeToString(scan())

    private fun detectRoot(): RootDetectionResult {
        val suBinary     = rootDetector.isSuBinaryPresent()
        val testKeys     = rootDetector.isTestKeysBuild()
        val superuserApk = rootDetector.isSuperuserApkPresent()

        return RootDetectionResult(
            suBinaryFound     = suBinary,
            testKeysFound     = testKeys,
            superuserApkFound = superuserApk,
        ).also {
            Timber.d(
                "DeviceScanner: root detection — su=$suBinary testKeys=$testKeys " +
                "superuserApk=$superuserApk isRooted=${it.isRooted}"
            )
        }
    }

    /**
     * Reads the security patch level from [Build.VERSION.SECURITY_PATCH].
     */
    internal fun readSecurityPatchDate(): String =
        Build.VERSION.SECURITY_PATCH?.takeIf { it.isNotBlank() } ?: "unknown"

    /**
     * Reads the verified boot state from `SystemProperties` via reflection.
     *
     * Returns one of "green", "yellow", "orange", "red", or "unknown".
     */
    internal fun readBootloaderState(): String =
        try {
            val systemPropertiesClass = Class.forName("android.os.SystemProperties")
            val getMethod: Method = systemPropertiesClass.getMethod("get", String::class.java, String::class.java)
            val value = getMethod.invoke(null, PROP_VERIFIED_BOOT_STATE, "unknown") as? String
            value?.takeIf { it.isNotBlank() } ?: "unknown"
        } catch (e: Exception) {
            Timber.w(e, "DeviceScanner: cannot read SystemProperties — returning 'unknown'")
            "unknown"
        }

    companion object {
        private const val PROP_VERIFIED_BOOT_STATE = "ro.boot.verifiedbootstate"
    }
}
