package com.aegis.agent.data.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.aegis.agent.domain.usecase.CollectAppInventoryUseCase
import com.aegis.agent.domain.usecase.CollectDeviceTelemetryUseCase
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import timber.log.Timber

/**
 * TelemetrySyncWorker — periodically collects device telemetry and uploads to AEGIS backend.
 *
 * Scheduled by WorkManager using [PeriodicWorkRequest] — see [AegisSdk] for scheduling logic.
 *
 * `@HiltWorker` + `@AssistedInject` is the pattern for injecting dependencies into WorkManager
 * Workers when using Hilt. The [HiltWorkerFactory] (configured in [AegisApplication])
 * creates this worker with its injected dependencies.
 *
 * Implementation detail:
 * - Uses [CoroutineWorker] so the work runs on a coroutine dispatcher (IO by default).
 * - Returns [Result.success] on completion, [Result.retry] on transient failures,
 *   [Result.failure] on permanent failures (e.g., security certificate errors).
 */
@HiltWorker
class TelemetrySyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    /** Prompt 1.2 — DeviceScanner wired via use case. */
    private val collectDeviceTelemetry: CollectDeviceTelemetryUseCase,
    /** Prompt 1.3 — AppIntelligenceCollector wired via use case. */
    private val collectAppInventory: CollectAppInventoryUseCase,
    // Prompt 2.1 — Upload (activated in next prompt):
    // private val uploadTelemetry: UploadTelemetryUseCase,
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        Timber.d("TelemetrySyncWorker: starting telemetry collection cycle")

        return try {
            // ------------------------------------------------------------------
            // Step 1: Collect device posture (Prompt 1.2)
            // ------------------------------------------------------------------
            val deviceReport = collectDeviceTelemetry()
                .getOrElse { e ->
                    Timber.e(e, "TelemetrySyncWorker: device scan failed — will retry")
                    return Result.retry()
                }

            Timber.i(
                "TelemetrySyncWorker: device scan complete — " +
                "rooted=${deviceReport.rootDetection.isRooted} " +
                "verdict=${deviceReport.integrityVerdict} " +
                "patch=${deviceReport.securityPatchDate}"
            )

            // ------------------------------------------------------------------
            // Step 2: Collect app inventory — delta-aware (Prompt 1.3)
            // ------------------------------------------------------------------
            val appSnapshot = collectAppInventory()
                .getOrElse { e ->
                    Timber.e(e, "TelemetrySyncWorker: app inventory failed — will retry")
                    return Result.retry()
                }

            Timber.i(
                "TelemetrySyncWorker: app inventory complete — " +
                "total=${appSnapshot.totalAppCount} " +
                "changed=${appSnapshot.apps.size} " +
                "isDelta=${appSnapshot.isDelta}"
            )

            // ------------------------------------------------------------------
            // Step 3: Upload to AEGIS backend (Prompt 2.1 — activate when ready)
            // ------------------------------------------------------------------
            // uploadTelemetry(deviceReport, appSnapshot).getOrElse { return Result.retry() }

            Result.success()
        } catch (e: Exception) {
            Timber.e(e, "TelemetrySyncWorker: unexpected failure")
            Result.retry()
        }
    }

    companion object {
        const val WORK_NAME = "aegis_telemetry_sync"
        const val TAG       = "aegis_worker"
    }
}
