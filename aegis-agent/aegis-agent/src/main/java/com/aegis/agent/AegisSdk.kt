package com.aegis.agent

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import com.aegis.agent.data.worker.TelemetrySyncWorker
import com.aegis.agent.di.AgentConfigHolder
import com.aegis.agent.domain.model.AgentConfig
import com.aegis.agent.domain.model.ScanTrigger
import timber.log.Timber
import java.util.concurrent.TimeUnit

/**
 * AegisSdk — the public entry point for embedding the AEGIS agent in a host app.
 *
 * Usage (in your host Application.onCreate):
 * ```kotlin
 * AegisSdk.init(
 *     context = this,
 *     config = AgentConfig(
 *         backendUrl = "https://api.aegis.internal",
 *         deviceId = deviceEnrollmentId,
 *         enrollmentToken = mdmProvisionedToken,
 *         isByodMode = false
 *     )
 * )
 * ```
 *
 * The SDK uses WorkManager so no explicit lifecycle management is needed —
 * WorkManager survives process death and device reboots automatically.
 */
object AegisSdk {

    private var isInitialised = false

    /**
     * Initialises the AEGIS agent and schedules the background telemetry sync.
     *
     * @param context Application context (never Activity context — to avoid leaks)
     * @param config  [AgentConfig] provisioned by the MDM / app configuration
     */
    fun init(context: Context, config: AgentConfig) {
        if (isInitialised) {
            Timber.w("AegisSdk.init() called more than once — skipping duplicate init")
            return
        }

        Timber.d("AegisSdk: initialising for device=${config.deviceId}")

        // Populate the config holder so Hilt-provided DeviceScanner / IntegrityApiClient
        // can read runtime values (cloudProjectNumber, deviceId) when the graph is first used.
        AgentConfigHolder.config = config

        schedulePeriodicSync(context, config)

        isInitialised = true
        Timber.i("AegisSdk: agent active — syncing every ${config.scanIntervalMin} minutes")
    }

    /**
     * Cancels all scheduled work and resets the SDK state.
     * Call this during device unenrollment.
     */
    fun shutdown(context: Context) {
        WorkManager.getInstance(context)
            .cancelAllWorkByTag(TelemetrySyncWorker.TAG)
        isInitialised = false
        Timber.i("AegisSdk: agent shut down — all scheduled work cancelled")
    }

    fun requestScanNow(context: Context) {
        val scanRequest = OneTimeWorkRequestBuilder<TelemetrySyncWorker>()
            .setInputData(
                workDataOf(TelemetrySyncWorker.INPUT_TRIGGER to ScanTrigger.MANUAL.name)
            )
            .addTag(TelemetrySyncWorker.TAG)
            .addTag(TelemetrySyncWorker.MANUAL_TAG)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            TelemetrySyncWorker.MANUAL_WORK_NAME,
            ExistingWorkPolicy.REPLACE,
            scanRequest
        )

        Timber.i("AegisSdk: manual scan requested")
    }

    // =========================================================================
    // Private helpers
    // =========================================================================

    private fun schedulePeriodicSync(context: Context, config: AgentConfig) {
        val intervalMin = config.scanIntervalMin.coerceAtLeast(15L) // WorkManager minimum

        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)     // Don't drain battery on low charge
            .build()

        val syncRequest = PeriodicWorkRequestBuilder<TelemetrySyncWorker>(
            repeatInterval = intervalMin,
            repeatIntervalTimeUnit = TimeUnit.MINUTES
        )
            .setInputData(
                workDataOf(TelemetrySyncWorker.INPUT_TRIGGER to ScanTrigger.PERIODIC.name)
            )
            .setConstraints(constraints)
            .addTag(TelemetrySyncWorker.TAG)
            .build()

        // KEEP_EXISTING — preserves existing schedule if already enqueued;
        // use UPDATE if you want to apply new config on every init
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            TelemetrySyncWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            syncRequest
        )
    }
}
