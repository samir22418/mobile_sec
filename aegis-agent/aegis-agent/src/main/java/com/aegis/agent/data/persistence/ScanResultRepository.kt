package com.aegis.agent.data.persistence

import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.ImportantLog
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
import com.aegis.agent.domain.model.ScanTrigger
import com.aegis.agent.domain.model.TelemetryPayload
import com.aegis.agent.domain.model.UploadStatus
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScanResultRepository @Inject constructor(
    private val dao: ScanRecordDao,
) {
    private val json = Json {
        prettyPrint = false
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun observeLatest(): Flow<ScanRecord?> =
        dao.observeLatest().map { entity -> entity?.toDomain() }

    fun observeById(id: Long): Flow<ScanRecord?> =
        dao.observeById(id).map { entity -> entity?.toDomain() }

    fun observeRecent(limit: Int = DEFAULT_RECENT_SCAN_LIMIT): Flow<List<ScanRecord>> =
        dao.observeRecent(limit).map { entities -> entities.map { it.toDomain() } }

    suspend fun getLatest(): ScanRecord? =
        dao.getLatest()?.toDomain()

    suspend fun markRunning(trigger: ScanTrigger): Long =
        dao.insert(
            ScanRecordEntity(
                status = ScanStatus.RUNNING.name,
                trigger = trigger.name,
                startedAtEpochMs = System.currentTimeMillis(),
            )
        ).also {
            dao.pruneOldRecords(MAX_SCAN_RECORDS)
        }

    suspend fun markSuccess(
        id: Long,
        deviceReport: DeviceReport,
        appSnapshot: AppSnapshot,
        importantLogs: List<ImportantLog> = emptyList(),
    ) {
        val current = dao.getById(id) ?: return
        val completedAtEpochMs = System.currentTimeMillis()
        val payloadId = TelemetryPayload.stablePayloadId(
            scanId = id,
            deviceId = deviceReport.deviceId,
            startedAtEpochMs = current.startedAtEpochMs,
        )

        dao.update(
            current.copy(
                status = ScanStatus.SUCCESS.name,
                completedAtEpochMs = completedAtEpochMs,
                payloadId = payloadId,
                payloadCreatedAtEpochMs = completedAtEpochMs,
                uploadStatus = UploadStatus.PENDING.name,
                retryCount = 0,
                lastUploadAttemptAtEpochMs = null,
                lastUploadError = null,
                uploadedAtEpochMs = null,
                deviceId = deviceReport.deviceId,
                isRooted = deviceReport.rootDetection.isRooted,
                securityPatchDate = deviceReport.securityPatchDate,
                bootloaderState = deviceReport.bootloaderState,
                totalAppCount = appSnapshot.totalAppCount,
                changedAppCount = appSnapshot.apps.size,
                isAppDelta = appSnapshot.isDelta,
                importantLogCount = importantLogs.size,
                errorMessage = null,
                deviceReportJson = json.encodeToString(deviceReport),
                appSnapshotJson = json.encodeToString(appSnapshot),
                importantLogsJson = json.encodeToString(importantLogs),
            )
        )
    }

    suspend fun markFailed(id: Long, error: Throwable) {
        markFailed(id, error.message ?: error::class.java.simpleName)
    }

    suspend fun markFailed(id: Long, message: String) {
        val current = dao.getById(id) ?: return
        dao.update(
            current.copy(
                status = ScanStatus.FAILED.name,
                completedAtEpochMs = System.currentTimeMillis(),
                uploadStatus = UploadStatus.NOT_READY.name,
                errorMessage = message,
            )
        )
    }

    suspend fun getPendingUploads(limit: Int = DEFAULT_UPLOAD_BATCH_SIZE): List<ScanRecord> =
        dao.getUploadCandidates(
            statuses = listOf(UploadStatus.PENDING.name, UploadStatus.FAILED.name),
            limit = limit,
        ).map { it.toDomain() }

    suspend fun markUploadAttempt(id: Long, attemptAtEpochMs: Long = System.currentTimeMillis()) {
        dao.markUploadAttempt(
            id = id,
            attemptAtEpochMs = attemptAtEpochMs,
        )
    }

    suspend fun markUploaded(id: Long, uploadedAtEpochMs: Long = System.currentTimeMillis()) {
        dao.markUploaded(
            id = id,
            uploadedAtEpochMs = uploadedAtEpochMs,
        )
        dao.pruneOldRecords(MAX_SCAN_RECORDS)
    }

    suspend fun markUploadFailed(
        id: Long,
        error: Throwable,
        attemptAtEpochMs: Long = System.currentTimeMillis(),
    ) {
        markUploadFailed(
            id = id,
            message = error.message ?: error::class.java.simpleName,
            attemptAtEpochMs = attemptAtEpochMs,
        )
    }

    suspend fun markUploadFailed(
        id: Long,
        message: String,
        attemptAtEpochMs: Long = System.currentTimeMillis(),
    ) {
        dao.markUploadFailed(
            id = id,
            attemptAtEpochMs = attemptAtEpochMs,
            error = message.take(MAX_UPLOAD_ERROR_LENGTH),
        )
    }

    suspend fun markUploadPending(id: Long) {
        dao.markUploadPending(id)
    }

    companion object {
        const val DATABASE_NAME = "aegis_agent.db"
        const val DEFAULT_UPLOAD_BATCH_SIZE = 10
        const val DEFAULT_RECENT_SCAN_LIMIT = 5
        private const val MAX_SCAN_RECORDS = 25
        private const val MAX_UPLOAD_ERROR_LENGTH = 1_000
    }
}
