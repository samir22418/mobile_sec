package com.aegis.agent.data.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.aegis.agent.data.logs.LogFilterAgent
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.ScanTrigger
import com.aegis.agent.domain.usecase.CollectAppInventoryUseCase
import com.aegis.agent.domain.usecase.CollectDeviceTelemetryUseCase
import com.aegis.agent.domain.usecase.UploadTelemetryUseCase
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import timber.log.Timber

/**
 * Periodically or manually collects AEGIS telemetry.
 *
 * Each run is persisted as a scan record:
 * - RUNNING when the worker starts
 * - SUCCESS when both device posture and app inventory complete
 * - FAILED when any stage throws or returns a failed Result
 */
@HiltWorker
class TelemetrySyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    private val collectDeviceTelemetry: CollectDeviceTelemetryUseCase,
    private val collectAppInventory: CollectAppInventoryUseCase,
    private val uploadTelemetry: UploadTelemetryUseCase,
    private val scanResultRepository: ScanResultRepository,
    private val logFilterAgent: LogFilterAgent,
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        Timber.d("TelemetrySyncWorker: starting telemetry collection cycle")

        val trigger = ScanTrigger.fromValue(inputData.getString(INPUT_TRIGGER))
        val scanRecordId = scanResultRepository.markRunning(trigger)

        return try {
            val deviceResult = collectDeviceTelemetry()
            if (deviceResult.isFailure) {
                val error = deviceResult.exceptionOrNull() ?: RuntimeException("Device scan failed")
                Timber.e(error, "TelemetrySyncWorker: device scan failed; will retry")
                scanResultRepository.markFailed(scanRecordId, error)
                return Result.retry()
            }
            val deviceReport = deviceResult.getOrThrow()

            Timber.i(
                "TelemetrySyncWorker: device scan complete; " +
                    "rooted=${deviceReport.rootDetection.isRooted} " +
                    "patch=${deviceReport.securityPatchDate}"
            )

            val appResult = collectAppInventory()
            if (appResult.isFailure) {
                val error = appResult.exceptionOrNull() ?: RuntimeException("App inventory failed")
                Timber.e(error, "TelemetrySyncWorker: app inventory failed; will retry")
                scanResultRepository.markFailed(scanRecordId, error)
                return Result.retry()
            }
            val appSnapshot = appResult.getOrThrow()

            Timber.i(
                "TelemetrySyncWorker: app inventory complete; " +
                    "total=${appSnapshot.totalAppCount} " +
                    "changed=${appSnapshot.apps.size} " +
                    "isDelta=${appSnapshot.isDelta}"
            )

            val importantLogs = runCatching {
                logFilterAgent.collectSnapshot()
            }.getOrElse { error ->
                Timber.w(error, "TelemetrySyncWorker: important log collection failed; continuing")
                emptyList()
            }

            Timber.i("TelemetrySyncWorker: important logs collected; count=${importantLogs.size}")

            scanResultRepository.markSuccess(
                id = scanRecordId,
                deviceReport = deviceReport,
                appSnapshot = appSnapshot,
                importantLogs = importantLogs,
            )

            val uploadResult = uploadTelemetry()
            if (uploadResult.isFailure) {
                val error = uploadResult.exceptionOrNull()
                    ?: RuntimeException("Telemetry upload failed")
                Timber.w(error, "TelemetrySyncWorker: upload queue failed; will retry")
                return Result.retry()
            }

            val uploadSummary = uploadResult.getOrThrow()
            Timber.i(
                "TelemetrySyncWorker: upload drain complete; " +
                    "attempted=${uploadSummary.attempted} " +
                    "uploaded=${uploadSummary.uploaded} " +
                    "failed=${uploadSummary.failed}"
            )

            if (uploadSummary.hasFailures) {
                Timber.w("TelemetrySyncWorker: upload failures remain queued; will retry")
                Result.retry()
            } else {
                Result.success()
            }
        } catch (e: Exception) {
            Timber.e(e, "TelemetrySyncWorker: unexpected failure")
            scanResultRepository.markFailed(scanRecordId, e)
            Result.retry()
        }
    }

    companion object {
        const val WORK_NAME = "aegis_telemetry_sync"
        const val MANUAL_WORK_NAME = "aegis_manual_scan"
        const val INPUT_TRIGGER = "aegis_scan_trigger"
        const val TAG = "aegis_worker"
        const val MANUAL_TAG = "aegis_manual_worker"
    }
}
