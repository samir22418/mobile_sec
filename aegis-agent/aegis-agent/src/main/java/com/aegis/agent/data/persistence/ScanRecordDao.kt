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

    @Query("SELECT * FROM scan_records ORDER BY started_at_epoch_ms DESC, id DESC LIMIT 1")
    suspend fun getLatest(): ScanRecordEntity?

    @Query(
        """
        DELETE FROM scan_records
        WHERE id NOT IN (
            SELECT id FROM scan_records ORDER BY started_at_epoch_ms DESC, id DESC LIMIT :keepCount
        )
        """
    )
    suspend fun pruneOldRecords(keepCount: Int)
}
