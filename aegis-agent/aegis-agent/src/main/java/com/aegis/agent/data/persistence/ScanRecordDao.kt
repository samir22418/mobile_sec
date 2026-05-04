package com.aegis.agent.data.persistence

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface ScanRecordDao {

    @Insert
    suspend fun insert(record: ScanRecordEntity): Long

    @Update
    suspend fun update(record: ScanRecordEntity)

    @Query("SELECT * FROM scan_records WHERE id = :id LIMIT 1")
    suspend fun getById(id: Long): ScanRecordEntity?

    @Query("SELECT * FROM scan_records ORDER BY started_at_epoch_ms DESC, id DESC LIMIT 1")
    fun observeLatest(): Flow<ScanRecordEntity?>

    @Query("SELECT * FROM scan_records WHERE id = :id LIMIT 1")
    fun observeById(id: Long): Flow<ScanRecordEntity?>

    @Query("SELECT * FROM scan_records ORDER BY started_at_epoch_ms DESC, id DESC LIMIT :limit")
    fun observeRecent(limit: Int): Flow<List<ScanRecordEntity>>

    @Query("SELECT * FROM scan_records ORDER BY started_at_epoch_ms DESC, id DESC LIMIT 1")
    suspend fun getLatest(): ScanRecordEntity?

    @Query(
        """
        SELECT * FROM scan_records
        WHERE upload_status IN (:statuses)
            AND status = 'SUCCESS'
            AND payload_id IS NOT NULL
            AND device_report_json IS NOT NULL
            AND app_snapshot_json IS NOT NULL
        ORDER BY started_at_epoch_ms ASC, id ASC
        LIMIT :limit
        """
    )
    suspend fun getUploadCandidates(
        statuses: List<String>,
        limit: Int,
    ): List<ScanRecordEntity>

    @Query(
        """
        UPDATE scan_records
        SET upload_status = 'UPLOADING',
            last_upload_attempt_at_epoch_ms = :attemptAtEpochMs,
            last_upload_error = NULL
        WHERE id = :id
        """
    )
    suspend fun markUploadAttempt(
        id: Long,
        attemptAtEpochMs: Long,
    )

    @Query(
        """
        UPDATE scan_records
        SET upload_status = 'UPLOADED',
            uploaded_at_epoch_ms = :uploadedAtEpochMs,
            last_upload_error = NULL
        WHERE id = :id
        """
    )
    suspend fun markUploaded(
        id: Long,
        uploadedAtEpochMs: Long,
    )

    @Query(
        """
        UPDATE scan_records
        SET upload_status = 'FAILED',
            retry_count = retry_count + 1,
            last_upload_attempt_at_epoch_ms = :attemptAtEpochMs,
            last_upload_error = :error
        WHERE id = :id
        """
    )
    suspend fun markUploadFailed(
        id: Long,
        attemptAtEpochMs: Long,
        error: String,
    )

    @Query(
        """
        UPDATE scan_records
        SET upload_status = 'PENDING',
            last_upload_error = NULL
        WHERE id = :id
        """
    )
    suspend fun markUploadPending(id: Long)

    @Query(
        """
        DELETE FROM scan_records
        WHERE upload_status NOT IN ('PENDING', 'UPLOADING', 'FAILED')
            AND id NOT IN (
                SELECT id FROM scan_records ORDER BY started_at_epoch_ms DESC, id DESC LIMIT :keepCount
        )
        """
    )
    suspend fun pruneOldRecords(keepCount: Int)
}
