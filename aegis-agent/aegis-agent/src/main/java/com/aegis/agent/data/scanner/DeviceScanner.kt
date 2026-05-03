package com.aegis.agent.data.scanner

import android.content.Context
import android.os.Build
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.IntegrityCheckResult
import com.aegis.agent.domain.model.IntegrityVerdict
import com.aegis.agent.domain.model.RootDetectionResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import timber.log.Timber
import java.lang.reflect.Method
import javax.inject.Inject
import javax.inject.Named

/**
 * DeviceScanner — orchestrates a full device security posture scan and returns
 * the result as a [DeviceReport] serialized to a JSON string.
 *
 * All public functions are **suspending** so callers (WorkManager coroutine workers,
 * use cases, tests) use structured concurrency without blocking a thread.
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
 *                 ──▶  IntegrityApiClient
 *                 ──▶  Build / SystemProperties
 * ```
 *
 * ## DI wiring
 * Injected by Hilt via [ScannerModule]. Named strings are used for the cloud
 * project number and device ID so they can be provided by [AgentConfig] without
 * creating a circular dependency in the DI graph.
 *
 * @param context            Application context (for Play Integrity API).
 * @param rootDetector       Performs the three root-detection checks.
 * @param integrityApiClient Wraps Play Integrity API calls as coroutines.
 * @param deviceId           Unique device identifier (from AgentConfig).
 */
class DeviceScanner @Inject constructor(
    private val context: Context,
    private val rootDetector: RootDetector,
    private val integrityApiClient: IntegrityApiClient,
    @Named("deviceId") private val deviceId: String,
    private val mainDispatcher: CoroutineDispatcher = Dispatchers.Main,
) {

    // =========================================================================
    // JSON serializer — lenient so that unknown fields from future schema
    // versions are silently ignored on round-trip.
    // =========================================================================
    private val json = Json {
        prettyPrint = false          // compact output for network transmission
        ignoreUnknownKeys = true
        encodeDefaults = true        // include isRooted composite field
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * Runs a full device security scan and returns a [DeviceReport].
     *
     * All blocking I/O (filesystem checks, reflection) is dispatched on
     * [Dispatchers.IO].  The Play Integrity callback is internally resumed
     * on the caller's thread by [IntegrityApiClient].
     *
     * @return A fully-populated [DeviceReport] snapshot.
     */
    suspend fun scan(): DeviceReport = withContext(Dispatchers.IO) {
        Timber.d("DeviceScanner: starting posture scan for device=$deviceId")

        val rootResult   = detectRoot()
        val patchDate    = readSecurityPatchDate()
        val bootloader   = readBootloaderState()

        // Play Integrity must be called from the Main thread (it's a Google
        // Play Services Tasks API).  Switch back to Main for the duration.
        val integrity = withContext(mainDispatcher) {
            queryIntegrity()
        }

        DeviceReport(
            deviceId           = deviceId,
            timestampEpochMs   = System.currentTimeMillis(),
            rootDetection      = rootResult,
            integrityVerdict   = integrity.verdict,
            integrityDetails   = integrity.details,
            integrityErrorCode = integrity.errorCode,
            integrityTokenHashSha256 = integrity.tokenHashSha256,
            securityPatchDate  = patchDate,
            bootloaderState    = bootloader,
        ).also {
            Timber.i(
                "DeviceScanner: scan complete — rooted=${it.rootDetection.isRooted} " +
                "verdict=${it.integrityVerdict} patch=${it.securityPatchDate} " +
                "bootloader=${it.bootloaderState}"
            )
        }
    }

    /**
     * Convenience overload: runs [scan] and serializes the result to a JSON string.
     *
     * Useful for direct upload to the AEGIS backend without an intermediate
     * deserialization step.
     *
     * @return Compact JSON representation of [DeviceReport].
     */
    suspend fun scanToJson(): String = json.encodeToString(scan())

    // =========================================================================
    // Root detection — three independent methods
    // =========================================================================

    /**
     * Runs all three root-detection heuristics and aggregates the results.
     *
     * Each method is independent — a `true` from any one is enough for the
     * backend to flag the device as rooted, but all signals are reported so
     * the backend risk engine can apply nuanced scoring.
     */
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

    // =========================================================================
    // Play Integrity API query
    // =========================================================================

    /**
     * Generates a nonce and queries the Play Integrity API for the device's
     * integrity verdict.
     *
     * **Nonce strategy:** For local-only assessment we use a simple nonce built
     * from the current timestamp + deviceId.  In a production flow the backend
     * should issue a server-side nonce (one-time challenge) before calling this
     * method so the returned token cannot be replayed.
     *
     * @return [IntegrityVerdict] — MEETS_STRONG_INTEGRITY, MEETS_DEVICE_INTEGRITY,
     *         MEETS_BASIC_INTEGRITY, or FAILS.
     */
    private suspend fun queryIntegrity(): IntegrityCheckResult {
        val nonce = buildNonce()
        return try {
            integrityApiClient.queryIntegrity(nonce)
        } catch (e: Exception) {
            Timber.e(e, "DeviceScanner: Play Integrity query failed")
            IntegrityCheckResult(
                verdict = IntegrityVerdict.API_ERROR,
                details = "Play Integrity query crashed locally: ${e.message ?: e::class.java.simpleName}",
            )
        }
    }

    /**
     * Builds a Base64url-encoded nonce from device ID and current timestamp.
     *
     * The nonce is at minimum 24 characters (16 bytes of entropy minimum per
     * Play Integrity API requirements).
     */
    private fun buildNonce(): String {
        val raw = "$deviceId:${System.currentTimeMillis()}"
        return java.util.Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString(raw.toByteArray(Charsets.UTF_8))
    }

    // =========================================================================
    // Security patch date
    // =========================================================================

    /**
     * Reads the security patch level from [Build.VERSION.SECURITY_PATCH].
     *
     * Returns the date string as-is (e.g. "2024-03-05") — the backend is
     * responsible for comparing it against the minimum acceptable patch date.
     *
     * @return ISO-8601 date string, or "unknown" if the field is blank/null.
     */
    internal fun readSecurityPatchDate(): String =
        Build.VERSION.SECURITY_PATCH?.takeIf { it.isNotBlank() } ?: "unknown"

    // =========================================================================
    // Bootloader state
    // =========================================================================

    /**
     * Reads the verified boot state from `SystemProperties`.
     *
     * The property `ro.boot.verifiedbootstate` is set by the bootloader and
     * reflects the chain-of-trust state:
     *  - **green**  — device is in locked state; boot chain is fully verified
     *  - **yellow** — device is using a user-installed key; likely custom ROM
     *  - **orange** — bootloader is unlocked; no chain of trust
     *  - **red**    — verification failed at some point in the boot chain
     *
     * Accessed via reflection because `SystemProperties` is a `@hide` API not
     * available in the public SDK.  The reflection call is safe to fail — we
     * return "unknown" rather than crashing.
     *
     * @return One of "green", "yellow", "orange", "red", or "unknown".
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
