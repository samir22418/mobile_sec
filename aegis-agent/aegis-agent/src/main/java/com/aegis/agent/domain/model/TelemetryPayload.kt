package com.aegis.agent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.nio.charset.StandardCharsets
import java.util.UUID

/**
 * Upload contract for one AEGIS telemetry submission.
 *
 * The payload combines one completed scan with the current enrollment token.
 * The token is intentionally not stored in Room; future upload code should
 * rebuild this object from the saved scan JSON plus encrypted AgentConfig.
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

    @SerialName("enrollment_token")
    val enrollmentToken: String,

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
        ): TelemetryPayload =
            TelemetryPayload(
                payloadId = stablePayloadId(
                    scanId = scanId,
                    deviceId = deviceReport.deviceId,
                    startedAtEpochMs = startedAtEpochMs,
                ),
                scanId = scanId,
                deviceId = deviceReport.deviceId,
                createdAtEpochMs = createdAtEpochMs,
                enrollmentToken = config.enrollmentToken,
                deviceReport = deviceReport,
                appSnapshot = appSnapshot,
                importantLogs = importantLogs,
            )

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
