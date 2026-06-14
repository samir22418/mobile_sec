package com.aegis.agent.domain.usecase

import com.aegis.agent.data.network.TelemetryUploadException
import com.aegis.agent.data.network.TelemetryUploader
import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.ImportantLog
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.TelemetryPayload
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import timber.log.Timber
import javax.inject.Inject

class UploadTelemetryUseCase @Inject constructor(
    private val configRepository: ConfigRepository,
    private val scanResultRepository: ScanResultRepository,
    private val telemetryUploader: TelemetryUploader,
) {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    suspend operator fun invoke(
        limit: Int = ScanResultRepository.DEFAULT_UPLOAD_BATCH_SIZE,
    ): Result<UploadTelemetrySummary> {
        val config = configRepository.load()
            ?: return Result.failure(IllegalStateException("AEGIS config is not persisted"))

        val candidates = scanResultRepository.getPendingUploads(limit)
        var uploaded = 0
        var failed = 0

        for (record in candidates) {
            val attemptAt = System.currentTimeMillis()
            scanResultRepository.markUploadAttempt(record.id, attemptAt)

            val payloadResult = buildPayload(record, config.enrollmentToken)
            if (payloadResult.isFailure) {
                failed += 1
                val error = payloadResult.exceptionOrNull()
                    ?: IllegalStateException("Failed to build telemetry payload")
                // Corrupt/missing JSON can never succeed on retry — dead-letter immediately.
                Timber.e(error, "UploadTelemetryUseCase: dead-lettering scan=${record.id} (payload build failed)")
                scanResultRepository.markDeadLetter(record.id, error, attemptAt)
                continue
            }

            val uploadResult = telemetryUploader.upload(
                backendUrl = config.backendUrl,
                payload = payloadResult.getOrThrow(),
            )

            if (uploadResult.isSuccess) {
                uploaded += 1
                scanResultRepository.markUploaded(record.id)
            } else {
                failed += 1
                val error = uploadResult.exceptionOrNull()
                    ?: IllegalStateException("Telemetry upload failed")
                val isRetryable = (error as? TelemetryUploadException)?.isRetryable ?: true
                val wouldExceedLimit = record.retryCount + 1 >= ScanResultRepository.MAX_UPLOAD_RETRIES
                if (!isRetryable || wouldExceedLimit) {
                    Timber.e(error, "UploadTelemetryUseCase: dead-lettering scan=${record.id} (retryable=$isRetryable, retries=${record.retryCount})")
                    scanResultRepository.markDeadLetter(record.id, error, attemptAt)
                } else {
                    Timber.w(error, "UploadTelemetryUseCase: upload failed for scan=${record.id}, retry ${record.retryCount + 1}/${ScanResultRepository.MAX_UPLOAD_RETRIES}")
                    scanResultRepository.markUploadFailed(record.id, error, attemptAt)
                }
            }
        }

        return Result.success(
            UploadTelemetrySummary(
                attempted = candidates.size,
                uploaded = uploaded,
                failed = failed,
            )
        )
    }

    internal fun buildPayload(
        record: ScanRecord,
        enrollmentToken: String,
    ): Result<TelemetryPayload> =
        runCatching {
            val deviceReportJson = record.deviceReportJson
                ?: throw IllegalStateException("Scan ${record.id} has no device report JSON")
            val appSnapshotJson = record.appSnapshotJson
                ?: throw IllegalStateException("Scan ${record.id} has no app snapshot JSON")

            val deviceReport = tryDecode<DeviceReport>(deviceReportJson, record.id, "device report")
            val appSnapshot = tryDecode<AppSnapshot>(appSnapshotJson, record.id, "app snapshot")
            val importantLogs = record.importantLogsJson
                ?.let { tryDecode<List<ImportantLog>>(it, record.id, "important logs") }
                ?: emptyList()

            TelemetryPayload(
                payloadId = record.payloadId
                    ?: TelemetryPayload.stablePayloadId(
                        scanId = record.id,
                        deviceId = deviceReport.deviceId,
                        startedAtEpochMs = record.startedAtEpochMs,
                    ),
                scanId = record.id,
                deviceId = deviceReport.deviceId,
                createdAtEpochMs = record.payloadCreatedAtEpochMs ?: System.currentTimeMillis(),
                enrollmentToken = enrollmentToken,
                deviceReport = deviceReport,
                appSnapshot = appSnapshot,
                importantLogs = importantLogs,
            )
        }

    private inline fun <reified T> tryDecode(
        value: String,
        scanId: Long,
        label: String,
    ): T =
        try {
            json.decodeFromString<T>(value)
        } catch (e: SerializationException) {
            throw IllegalStateException("Scan $scanId has invalid $label JSON", e)
        } catch (e: IllegalArgumentException) {
            throw IllegalStateException("Scan $scanId has invalid $label JSON", e)
        }
}

data class UploadTelemetrySummary(
    val attempted: Int,
    val uploaded: Int,
    val failed: Int,
) {
    val hasFailures: Boolean
        get() = failed > 0
}
