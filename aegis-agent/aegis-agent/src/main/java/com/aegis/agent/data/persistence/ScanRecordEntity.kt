package com.aegis.agent.data.persistence

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
import com.aegis.agent.domain.model.ScanTrigger
import com.aegis.agent.domain.model.UploadStatus

@Entity(tableName = "scan_records")
data class ScanRecordEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0L,

    @ColumnInfo(name = "status")
    val status: String,

    @ColumnInfo(name = "trigger")
    val trigger: String,

    @ColumnInfo(name = "started_at_epoch_ms")
    val startedAtEpochMs: Long,

    @ColumnInfo(name = "completed_at_epoch_ms")
    val completedAtEpochMs: Long? = null,

    @ColumnInfo(name = "payload_id")
    val payloadId: String? = null,

    @ColumnInfo(name = "payload_created_at_epoch_ms")
    val payloadCreatedAtEpochMs: Long? = null,

    @ColumnInfo(name = "upload_status")
    val uploadStatus: String = UploadStatus.NOT_READY.name,

    @ColumnInfo(name = "retry_count")
    val retryCount: Int = 0,

    @ColumnInfo(name = "last_upload_attempt_at_epoch_ms")
    val lastUploadAttemptAtEpochMs: Long? = null,

    @ColumnInfo(name = "last_upload_error")
    val lastUploadError: String? = null,

    @ColumnInfo(name = "uploaded_at_epoch_ms")
    val uploadedAtEpochMs: Long? = null,

    @ColumnInfo(name = "device_id")
    val deviceId: String? = null,

    @ColumnInfo(name = "is_rooted")
    val isRooted: Boolean? = null,

    @ColumnInfo(name = "security_patch_date")
    val securityPatchDate: String? = null,

    @ColumnInfo(name = "bootloader_state")
    val bootloaderState: String? = null,

    @ColumnInfo(name = "total_app_count")
    val totalAppCount: Int? = null,

    @ColumnInfo(name = "changed_app_count")
    val changedAppCount: Int? = null,

    @ColumnInfo(name = "is_app_delta")
    val isAppDelta: Boolean? = null,

    @ColumnInfo(name = "important_log_count")
    val importantLogCount: Int = 0,

    @ColumnInfo(name = "error_message")
    val errorMessage: String? = null,

    @ColumnInfo(name = "device_report_json")
    val deviceReportJson: String? = null,

    @ColumnInfo(name = "app_snapshot_json")
    val appSnapshotJson: String? = null,

    @ColumnInfo(name = "important_logs_json")
    val importantLogsJson: String? = null,
) {
    fun toDomain(): ScanRecord = ScanRecord(
        id = id,
        status = ScanStatus.fromValue(status),
        trigger = ScanTrigger.fromValue(trigger),
        startedAtEpochMs = startedAtEpochMs,
        completedAtEpochMs = completedAtEpochMs,
        payloadId = payloadId,
        payloadCreatedAtEpochMs = payloadCreatedAtEpochMs,
        uploadStatus = UploadStatus.fromValue(uploadStatus),
        retryCount = retryCount,
        lastUploadAttemptAtEpochMs = lastUploadAttemptAtEpochMs,
        lastUploadError = lastUploadError,
        uploadedAtEpochMs = uploadedAtEpochMs,
        deviceId = deviceId,
        isRooted = isRooted,
        securityPatchDate = securityPatchDate,
        bootloaderState = bootloaderState,
        totalAppCount = totalAppCount,
        changedAppCount = changedAppCount,
        isAppDelta = isAppDelta,
        importantLogCount = importantLogCount,
        errorMessage = errorMessage,
        deviceReportJson = deviceReportJson,
        appSnapshotJson = appSnapshotJson,
        importantLogsJson = importantLogsJson,
    )
}
