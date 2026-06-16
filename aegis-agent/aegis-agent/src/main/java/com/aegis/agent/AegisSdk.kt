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
import com.aegis.agent.data.logs.LogFilterAgent
import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.data.worker.TelemetrySyncWorker
import com.aegis.agent.di.AgentConfigHolder
import com.aegis.agent.domain.model.AgentConfig
import com.aegis.agent.domain.model.ScanTrigger
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent
import timber.log.Timber
import java.util.concurrent.TimeUnit

/**
 * Public entry point for embedding the AEGIS agent in a host app.
 *
 * The SDK uses WorkManager for background scans and persists AgentConfig so the
 * schedule can be restored after process death or device reboot.
 */
object AegisSdk {

    private var isInitialised = false

    /**
     * Initialises the AEGIS agent and schedules the background telemetry sync.
     *
     * @param context Application context. Activity context is accepted but not retained.
     * @param config AgentConfig provisioned by the MDM or host app configuration.
     */
    fun init(context: Context, config: AgentConfig) {
        val appContext = context.applicationContext
        val configRepository = ConfigRepository(appContext)

        if (!configRepository.save(config)) {
            Timber.w("AegisSdk: config persistence failed; continuing with in-memory config")
        }
        AgentConfigHolder.config = config

        if (isInitialised) {
            Timber.w("AegisSdk.init() called more than once - refreshed stored config only")
            return
        }

        Timber.d("AegisSdk: initialising for device=${config.deviceId}")

        startLogCollection(appContext)
        schedulePeriodicSync(appContext, config)

        isInitialised = true
        Timber.i("AegisSdk: agent active - syncing every ${config.scanIntervalMin} minutes")
    }

    /**
     * Cancels all scheduled work, clears persisted config, and resets SDK state.
     * Call this during device unenrollment.
     */
    fun shutdown(context: Context) {
        val appContext = context.applicationContext
        stopLogCollection(appContext)
        WorkManager.getInstance(appContext)
            .cancelAllWorkByTag(TelemetrySyncWorker.TAG)
        ConfigRepository(appContext).clear()
        AgentConfigHolder.config = null
        isInitialised = false
        Timber.i("AegisSdk: agent shut down - scheduled work cancelled and config cleared")
    }

    fun requestScanNow(context: Context) {
        val appContext = context.applicationContext
        val scanRequest = OneTimeWorkRequestBuilder<TelemetrySyncWorker>()
            .setInputData(
                workDataOf(TelemetrySyncWorker.INPUT_TRIGGER to ScanTrigger.MANUAL.name)
            )
            .addTag(TelemetrySyncWorker.TAG)
            .addTag(TelemetrySyncWorker.MANUAL_TAG)
            .build()

        WorkManager.getInstance(appContext).enqueueUniqueWork(
            TelemetrySyncWorker.MANUAL_WORK_NAME,
            ExistingWorkPolicy.REPLACE,
            scanRequest
        )

        Timber.i("AegisSdk: manual scan requested")
    }

    internal fun initFromPersistedConfig(context: Context): Boolean {
        val appContext = context.applicationContext
        val config = AgentConfigHolder.config
            ?: ConfigRepository(appContext).load()?.also { AgentConfigHolder.config = it }

        if (config == null) {
            Timber.w("AegisSdk: no persisted config available for restore")
            return false
        }

        init(appContext, config)
        return true
    }

    private fun schedulePeriodicSync(context: Context, config: AgentConfig) {
        val intervalMin = config.scanIntervalMin.coerceAtLeast(15L) // WorkManager minimum

        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
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

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            TelemetrySyncWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            syncRequest
        )
    }

    private fun startLogCollection(context: Context) {
        runCatching {
            sdkEntryPoint(context).logFilterAgent().start()
        }.onFailure { error ->
            Timber.w(error, "AegisSdk: log collection could not be started")
        }
    }

    private fun stopLogCollection(context: Context) {
        runCatching {
            sdkEntryPoint(context).logFilterAgent().stop()
        }.onFailure { error ->
            Timber.w(error, "AegisSdk: log collection could not be stopped")
        }
    }

    private fun sdkEntryPoint(context: Context): AegisSdkEntryPoint =
        EntryPointAccessors.fromApplication(
            context.applicationContext,
            AegisSdkEntryPoint::class.java,
        )

    @EntryPoint
    @InstallIn(SingletonComponent::class)
    internal interface AegisSdkEntryPoint {
        fun logFilterAgent(): LogFilterAgent
    }
}
