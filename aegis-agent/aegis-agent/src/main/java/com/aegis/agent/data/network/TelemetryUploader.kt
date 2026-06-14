package com.aegis.agent.data.network

import com.aegis.agent.domain.model.TelemetryPayload
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TelemetryUploader @Inject constructor(
    private val client: OkHttpClient,
) {
    private val json = Json {
        prettyPrint = false
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    suspend fun upload(
        backendUrl: String,
        payload: TelemetryPayload,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        runCatching {
            val requestBody = json.encodeToString(payload)
                .toRequestBody(JSON_MEDIA_TYPE)

            val request = Request.Builder()
                .url(telemetryUrl(backendUrl))
                .post(requestBody)
                .header("Accept", "application/json")
                .header("X-Aegis-Payload-Id", payload.payloadId)
                .header("X-Aegis-Device-Id", payload.deviceId)
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val body = response.body?.string()?.take(MAX_ERROR_BODY_LENGTH)
                    throw TelemetryUploadException(
                        statusCode = response.code,
                        responseBody = body,
                    )
                }
            }

            Timber.i("TelemetryUploader: uploaded payload=${payload.payloadId}")
        }
    }

    internal fun telemetryUrl(backendUrl: String): String {
        val trimmed = backendUrl.trim().trimEnd('/')
        require(trimmed.isNotBlank()) { "backendUrl is blank" }
        return "$trimmed/api/v1/telemetry"
    }

    companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
        private const val MAX_ERROR_BODY_LENGTH = 500
    }
}

class TelemetryUploadException(
    val statusCode: Int,
    val responseBody: String?,
) : Exception("Telemetry upload failed with HTTP $statusCode${responseBody?.let { ": $it" }.orEmpty()}") {
    // 5xx and 429 are transient — safe to retry. 4xx (except 429) means the payload is rejected.
    val isRetryable: Boolean get() = statusCode >= 500 || statusCode == 429
}
