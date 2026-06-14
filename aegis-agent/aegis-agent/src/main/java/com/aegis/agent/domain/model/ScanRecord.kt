package com.aegis.agent.domain.model

/**
 * Lifecycle state for a scan run.
 */
enum class ScanStatus {
    RUNNING,
    SUCCESS,
    FAILED;

    companion object {
        fun fromValue(value: String?): ScanStatus =
            entries.firstOrNull { it.name == value } ?: FAILED
    }
}

/**
 * Describes why a scan was started.
 */
enum class ScanTrigger {
    PERIODIC,
    MANUAL;

    companion object {
        fun fromValue(value: String?): ScanTrigger =
            entries.firstOrNull { it.name == value } ?: PERIODIC
    }
}

/**
 * Upload lifecycle for a completed scan payload.
 *
 * DEAD_LETTER is a terminal failure state: the payload was rejected by the server (4xx) or
 * exhausted all retries. It is never re-queued automatically.
 */
enum class UploadStatus {
    NOT_READY,
    PENDING,
    UPLOADING,
    UPLOADED,
    FAILED,
    DEAD_LETTER;

    companion object {
        fun fromValue(value: String?): UploadStatus =
            entries.firstOrNull { it.name == value } ?: NOT_READY
    }
}

/**
 * Durable summary of one scan run.
 *
 * The JSON fields keep the complete payloads for future upload/retry flows, while
 * the summary fields let the UI render quickly without parsing large JSON blobs.
 */
data class ScanRecord(
    val id: Long,
    val status: ScanStatus,
    val trigger: ScanTrigger,
    val startedAtEpochMs: Long,
    val completedAtEpochMs: Long?,
    val payloadId: String?,
    val payloadCreatedAtEpochMs: Long?,
    val uploadStatus: UploadStatus,
    val retryCount: Int,
    val lastUploadAttemptAtEpochMs: Long?,
    val lastUploadError: String?,
    val uploadedAtEpochMs: Long?,
    val deviceId: String?,
    val isRooted: Boolean?,
    val integrityVerdict: IntegrityVerdict?,
    val integrityDetails: String?,
    val integrityErrorCode: Int?,
    val integrityTokenHashSha256: String?,
    val securityPatchDate: String?,
    val bootloaderState: String?,
    val totalAppCount: Int?,
    val changedAppCount: Int?,
    val isAppDelta: Boolean?,
    val importantLogCount: Int,
    val errorMessage: String?,
    val deviceReportJson: String?,
    val appSnapshotJson: String?,
    val importantLogsJson: String?,
)
