package com.aegis.agent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.nio.charset.StandardCharsets
import java.util.UUID

/**
 * Upload contract for one AEGIS telemetry submission.
 *
 * The enrollment token is sent as an Authorization bearer header by the
 * OkHttp client, not as plaintext in this JSON body.
 */
@Serializable
data class TelemetryPayload(
    @SerialName("payload_id")
    val payloadId: String,

    @SerialName("scan_id")
    val scanId: Long,

    @SerialName("device_id")
    val deviceId: String,

    @SerialName("created_at_epoch_ms")
    val createdAtEpochMs: Long,

    @SerialName("device_report")
    val deviceReport: DeviceReport,

    @SerialName("app_snapshot")
    val appSnapshot: AppSnapshot,

    @SerialName("important_logs")
    val importantLogs: List<ImportantLog> = emptyList(),
) {
    companion object {
        fun create(
            scanId: Long,
            startedAtEpochMs: Long,
            createdAtEpochMs: Long,
            config: AgentConfig,
            deviceReport: DeviceReport,
            appSnapshot: AppSnapshot,
            importantLogs: List<ImportantLog> = emptyList(),
        ): TelemetryPayload {
            val resolvedDeviceId = deviceReport.deviceId.ifBlank { config.deviceId }
            return TelemetryPayload(
                payloadId = stablePayloadId(
                    scanId = scanId,
                    deviceId = resolvedDeviceId,
                    startedAtEpochMs = startedAtEpochMs,
                ),
                scanId = scanId,
                deviceId = resolvedDeviceId,
                createdAtEpochMs = createdAtEpochMs,
                deviceReport = deviceReport,
                appSnapshot = appSnapshot,
                importantLogs = importantLogs,
            )
        }

        fun stablePayloadId(
            scanId: Long,
            deviceId: String,
            startedAtEpochMs: Long,
        ): String {
            val raw = "aegis:$deviceId:$scanId:$startedAtEpochMs"
            return UUID.nameUUIDFromBytes(raw.toByteArray(StandardCharsets.UTF_8)).toString()
        }
    }
}
