package com.aegis.agent.data.persistence

import com.aegis.agent.domain.model.AppSnapshot
import com.aegis.agent.domain.model.DeviceReport
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
import com.aegis.agent.domain.model.ScanTrigger
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
    ) {
        val current = dao.getById(id) ?: return
        dao.update(
            current.copy(
                status = ScanStatus.SUCCESS.name,
                completedAtEpochMs = System.currentTimeMillis(),
                deviceId = deviceReport.deviceId,
                isRooted = deviceReport.rootDetection.isRooted,
                integrityVerdict = deviceReport.integrityVerdict.name,
                integrityDetails = deviceReport.integrityDetails,
                integrityErrorCode = deviceReport.integrityErrorCode,
                integrityTokenHashSha256 = deviceReport.integrityTokenHashSha256,
                securityPatchDate = deviceReport.securityPatchDate,
                bootloaderState = deviceReport.bootloaderState,
                totalAppCount = appSnapshot.totalAppCount,
                changedAppCount = appSnapshot.apps.size,
                isAppDelta = appSnapshot.isDelta,
                errorMessage = null,
                deviceReportJson = json.encodeToString(deviceReport),
                appSnapshotJson = json.encodeToString(appSnapshot),
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
                errorMessage = message,
            )
        )
    }

    companion object {
        const val DATABASE_NAME = "aegis_agent.db"
        private const val MAX_SCAN_RECORDS = 25
    }
}
