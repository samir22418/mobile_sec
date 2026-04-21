package com.aegis.agent.data.scanner

import android.content.Context
import com.aegis.agent.domain.model.IntegrityVerdict
import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.IntegrityTokenRequest
import com.google.android.play.core.integrity.IntegrityTokenResponse
import kotlinx.coroutines.suspendCancellableCoroutine
import timber.log.Timber
import kotlin.coroutines.resume

/**
 * IntegrityApiClient — a **suspending** wrapper around the Google Play Integrity API.
 *
 * The Play Integrity SDK uses a callback-based API ([addOnSuccessListener] /
 * [addOnFailureListener]).  This class adapts that callback into a proper Kotlin
 * coroutine using [suspendCancellableCoroutine] so callers can use `await`-style
 * semantics without converting everything to RxJava or LiveData.
 *
 * **Coroutine cancellation:** The coroutine is cancellable — if the caller's scope
 * is cancelled while waiting for the Play Integrity response, the continuation is
 * abandoned (Google's Task does not have a cancel() API, but we at least stop
 * blocking the caller).
 *
 * **Backend verification:** The token returned here is a JWS (JSON Web Signature)
 * that MUST be verified server-side against Google's Play Integrity API.  Never
 * trust the local verdict label alone — a malicious app could fake it.
 *
 * @param context Application context (used to create the IntegrityManager)
 * @param cloudProjectNumber Your Google Cloud project number (numeric), obtained
 *   from the Google Play Console → Setup → API services.  Pass via [AgentConfig]
 *   or BuildConfig — never hard-code in source.
 */
class IntegrityApiClient(
    private val context: Context,
    private val cloudProjectNumber: Long,
) {

    /**
     * Requests a Play Integrity token and maps the verdict labels in the decoded
     * token payload into an [IntegrityVerdict] enum value.
     *
     * **Nonce requirement:** The nonce must be:
     * - A Base64-encoded string (URL-safe, no padding)
     * - At least 16 bytes of random data
     * - Unique per request (to prevent replay attacks)
     *
     * In production the nonce should be a HMAC of deviceId + timestamp, or a
     * server-issued challenge.  We pass it in so the caller can supply the right
     * value per its security policy.
     *
     * @param nonce Base64url-encoded, server-generated nonce.
     * @return [IntegrityVerdict] mapped from the strongest label in the response,
     *         or [IntegrityVerdict.FAILS] if the API call fails or returns no label.
     */
    suspend fun queryIntegrity(nonce: String): IntegrityVerdict =
        suspendCancellableCoroutine { continuation ->
            val integrityManager = IntegrityManagerFactory.create(context)

            val tokenRequest = IntegrityTokenRequest.builder()
                .setNonce(nonce)
                .setCloudProjectNumber(cloudProjectNumber)
                .build()

            integrityManager
                .requestIntegrityToken(tokenRequest)
                .addOnSuccessListener { response: IntegrityTokenResponse ->
                    val verdict = mapVerdictFromToken(response.token())
                    Timber.d("IntegrityApiClient: verdict=$verdict")
                    // resume() is safe to call from any thread — the coroutine
                    // dispatcher handles thread-hopping automatically.
                    continuation.resume(verdict)
                }
                .addOnFailureListener { exception ->
                    Timber.w(exception as Throwable, "IntegrityApiClient: API call failed")
                    // Map known error codes to a structured failure log, then
                    // degrade gracefully with FAILS (backend will flag for review).
                    logIntegrityError(exception)
                    continuation.resume(IntegrityVerdict.FAILS)
                }
        }

    // =========================================================================
    // Verdict mapping
    // =========================================================================

    /**
     * Maps the raw JWS token's device integrity labels to an [IntegrityVerdict].
     *
     * The Play Integrity verdict payload contains a `deviceIntegrity.deviceRecognitionVerdict`
     * array.  Labels are cumulative — MEETS_STRONG_INTEGRITY also implies
     * MEETS_DEVICE_INTEGRITY and MEETS_BASIC_INTEGRITY.
     *
     * Since the token must be decoded server-side for production use, this local
     * mapping is a best-effort for immediate risk gating (e.g., block a UI action
     * before the backend has processed the token).
     *
     * @param token The raw JWS token string from [IntegrityTokenResponse.token].
     * @return The strongest applicable [IntegrityVerdict].
     */
    internal fun mapVerdictFromToken(token: String): IntegrityVerdict {
        // The JWS payload is Base64url-encoded; decode the middle (payload) part.
        return try {
            val parts = token.split(".")
            if (parts.size < 2) return IntegrityVerdict.FAILS

            val payloadJson = String(
                android.util.Base64.decode(
                    parts[1],
                    android.util.Base64.URL_SAFE or android.util.Base64.NO_PADDING
                )
            )

            when {
                payloadJson.contains("MEETS_STRONG_INTEGRITY") -> IntegrityVerdict.MEETS_STRONG_INTEGRITY
                payloadJson.contains("MEETS_DEVICE_INTEGRITY") -> IntegrityVerdict.MEETS_DEVICE_INTEGRITY
                payloadJson.contains("MEETS_BASIC_INTEGRITY")  -> IntegrityVerdict.MEETS_BASIC_INTEGRITY
                else                                           -> IntegrityVerdict.FAILS
            }
        } catch (e: Exception) {
            Timber.w(e, "IntegrityApiClient: failed to decode token payload")
            IntegrityVerdict.FAILS
        }
    }

    private fun logIntegrityError(exception: Exception) {
        val msg = exception.message ?: "(no message)"
        val description = when {
            msg.contains("API_NOT_AVAILABLE", ignoreCase = true) ->
                "Play Integrity API not available — device may not have Play Services"
            msg.contains("PLAY_STORE_NOT_FOUND", ignoreCase = true) ->
                "Play Store not found — sideloaded or work profile without Play"
            msg.contains("NETWORK_ERROR", ignoreCase = true) ->
                "Network error — offline or captive portal"
            msg.contains("APP_NOT_INSTALLED", ignoreCase = true) ->
                "App not recognized by Play — first-run or sideload scenario"
            msg.contains("TOO_MANY_REQUESTS", ignoreCase = true) ->
                "Rate limited — too many integrity requests"
            else ->
                "Unknown integrity error: $msg"
        }
        Timber.w("IntegrityApiClient: $description")
    }
}
