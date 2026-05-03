package com.aegis.agent.data.scanner

import android.content.Context
import com.aegis.agent.domain.model.IntegrityCheckResult
import com.aegis.agent.domain.model.IntegrityVerdict
import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.IntegrityServiceException
import com.google.android.play.core.integrity.IntegrityTokenRequest
import com.google.android.play.core.integrity.IntegrityTokenResponse
import com.google.android.play.core.integrity.model.IntegrityErrorCode
import kotlinx.coroutines.suspendCancellableCoroutine
import timber.log.Timber
import java.security.MessageDigest
import kotlin.coroutines.resume

/**
 * Suspending wrapper around Google Play Integrity.
 *
 * The app client can request an encrypted token, but it cannot safely decode the
 * final verdict. Production code must send the token to a trusted backend and
 * call Google's decodeIntegrityToken flow there. This class therefore returns
 * REQUIRES_BACKEND_VERIFICATION when a token is received successfully.
 */
class IntegrityApiClient(
    private val context: Context,
    private val cloudProjectNumber: Long,
) {

    suspend fun queryIntegrity(nonce: String): IntegrityCheckResult {
        if (cloudProjectNumber <= 0L) {
            return IntegrityCheckResult(
                verdict = IntegrityVerdict.NOT_CONFIGURED,
                details = "Play Integrity is not configured. Set AgentConfig.cloudProjectNumber to the Google Cloud project number where Play Integrity API is enabled.",
            ).also {
                Timber.w("IntegrityApiClient: missing cloudProjectNumber")
            }
        }

        return suspendCancellableCoroutine { continuation ->
            val integrityManager = IntegrityManagerFactory.create(context)

            val tokenRequest = IntegrityTokenRequest.builder()
                .setNonce(nonce)
                .setCloudProjectNumber(cloudProjectNumber)
                .build()

            integrityManager
                .requestIntegrityToken(tokenRequest)
                .addOnSuccessListener { response: IntegrityTokenResponse ->
                    val tokenHash = sha256(response.token())
                    val result = IntegrityCheckResult(
                        verdict = IntegrityVerdict.REQUIRES_BACKEND_VERIFICATION,
                        details = "Play Integrity token received. Send it to the backend and decode it there for MEETS_* or FAILS.",
                        tokenHashSha256 = tokenHash,
                    )
                    Timber.i("IntegrityApiClient: token received hash=$tokenHash")
                    if (continuation.isActive) continuation.resume(result)
                }
                .addOnFailureListener { exception ->
                    val result = mapFailure(exception)
                    Timber.w(exception, "IntegrityApiClient: ${result.details}")
                    if (continuation.isActive) continuation.resume(result)
                }
        }
    }

    /**
     * Maps a backend-decoded payload JSON into the local enum.
     *
     * This helper is only for tests or future backend response handling. It must
     * not be used on the encrypted token returned directly to the Android client.
     */
    internal fun mapDecodedPayloadToVerdict(payloadJson: String): IntegrityVerdict =
        when {
            payloadJson.contains("MEETS_STRONG_INTEGRITY") -> IntegrityVerdict.MEETS_STRONG_INTEGRITY
            payloadJson.contains("MEETS_DEVICE_INTEGRITY") -> IntegrityVerdict.MEETS_DEVICE_INTEGRITY
            payloadJson.contains("MEETS_BASIC_INTEGRITY") -> IntegrityVerdict.MEETS_BASIC_INTEGRITY
            else -> IntegrityVerdict.FAILS
        }

    private fun mapFailure(exception: Exception): IntegrityCheckResult {
        val errorCode = (exception as? IntegrityServiceException)?.errorCode
        val verdict = when (errorCode) {
            IntegrityErrorCode.CLOUD_PROJECT_NUMBER_IS_INVALID -> IntegrityVerdict.NOT_CONFIGURED
            IntegrityErrorCode.API_NOT_AVAILABLE,
            IntegrityErrorCode.PLAY_STORE_NOT_FOUND,
            IntegrityErrorCode.PLAY_STORE_VERSION_OUTDATED,
            IntegrityErrorCode.PLAY_SERVICES_NOT_FOUND,
            IntegrityErrorCode.PLAY_SERVICES_VERSION_OUTDATED,
            IntegrityErrorCode.CANNOT_BIND_TO_SERVICE -> IntegrityVerdict.UNAVAILABLE
            IntegrityErrorCode.NETWORK_ERROR,
            IntegrityErrorCode.TOO_MANY_REQUESTS,
            IntegrityErrorCode.GOOGLE_SERVER_UNAVAILABLE,
            IntegrityErrorCode.INTERNAL_ERROR,
            IntegrityErrorCode.CLIENT_TRANSIENT_ERROR -> IntegrityVerdict.API_ERROR
            else -> IntegrityVerdict.FAILS
        }

        return IntegrityCheckResult(
            verdict = verdict,
            details = describeFailure(errorCode, exception),
            errorCode = errorCode,
        )
    }

    private fun describeFailure(errorCode: Int?, exception: Exception): String =
        when (errorCode) {
            IntegrityErrorCode.API_NOT_AVAILABLE ->
                "Play Integrity API is unavailable. Enable it in Play Console and update Play Store."
            IntegrityErrorCode.PLAY_STORE_NOT_FOUND ->
                "Official Google Play Store is missing or unavailable on this device."
            IntegrityErrorCode.PLAY_STORE_VERSION_OUTDATED ->
                "Google Play Store is outdated. Update Play Store and retry."
            IntegrityErrorCode.PLAY_SERVICES_NOT_FOUND ->
                "Google Play services are missing or too old on this device."
            IntegrityErrorCode.PLAY_SERVICES_VERSION_OUTDATED ->
                "Google Play services are outdated. Update Google Play services and retry."
            IntegrityErrorCode.PLAY_STORE_ACCOUNT_NOT_FOUND ->
                "No Play Store account is available on this device."
            IntegrityErrorCode.CANNOT_BIND_TO_SERVICE ->
                "Play Integrity could not bind to Play Store services. Update Play Store and retry."
            IntegrityErrorCode.CLOUD_PROJECT_NUMBER_IS_INVALID ->
                "Cloud project number is invalid. Use the numeric Google Cloud project number with Play Integrity enabled."
            IntegrityErrorCode.NETWORK_ERROR ->
                "Network is unavailable. Connect the device to the internet and retry."
            IntegrityErrorCode.TOO_MANY_REQUESTS ->
                "Play Integrity request was rate limited. Retry later."
            IntegrityErrorCode.GOOGLE_SERVER_UNAVAILABLE,
            IntegrityErrorCode.INTERNAL_ERROR,
            IntegrityErrorCode.CLIENT_TRANSIENT_ERROR ->
                "Temporary Play Integrity service error. Retry with backoff."
            IntegrityErrorCode.NONCE_IS_NOT_BASE64 ->
                "Nonce is not Base64 web-safe encoded."
            IntegrityErrorCode.NONCE_TOO_SHORT ->
                "Nonce is too short. It must be at least 16 bytes before Base64 encoding."
            IntegrityErrorCode.NONCE_TOO_LONG ->
                "Nonce is too long. It must be less than 500 bytes before Base64 encoding."
            IntegrityErrorCode.APP_NOT_INSTALLED ->
                "Play Integrity reports the calling app is not installed."
            IntegrityErrorCode.APP_UID_MISMATCH ->
                "Play Integrity reports the calling app UID does not match Package Manager."
            else ->
                "Play Integrity failed: ${exception.message ?: exception::class.java.simpleName}"
        }

    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8))
        return digest.joinToString(separator = "") { byte -> "%02x".format(byte) }
    }
}
