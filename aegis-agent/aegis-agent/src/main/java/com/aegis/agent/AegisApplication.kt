package com.aegis.agent

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import timber.log.Timber
import javax.inject.Inject

/**
 * AegisApplication — base Application class for the AEGIS agent.
 *
 * Responsibilities:
 * 1. Provide WorkManager a HiltWorkerFactory so Workers can receive @Inject fields
 * 2. Initialize Timber logging (debug builds only — never logs to prod)
 *
 * Architecture note:
 *   This class lives in the :aegis-agent library module. When embedded into a host
 *   app, the host's Application should extend AegisApplication AND be annotated
 *   with @HiltAndroidApp.
 */
open class AegisApplication : Application(), Configuration.Provider {

    /**
     * Hilt injects the WorkerFactory that knows how to create Hilt-aware Workers.
     * Without this, @Inject inside a Worker would silently be null.
     */
    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()

        initLogging()

        Timber.d("AEGIS Agent initialised — package: $packageName")
    }

    // -------------------------------------------------------------------------
    // WorkManager Configuration.Provider
    // -------------------------------------------------------------------------

    /**
     * Returns a custom WorkManager [Configuration] that plugs in [HiltWorkerFactory].
     *
     * Called by WorkManager on first use instead of the default auto-init.
     * The AndroidManifest removes the default WorkManagerInitializer so this
     * provider is the single source of configuration.
     */
    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .setMinimumLoggingLevel(
                if (BuildConfig.DEBUG) android.util.Log.DEBUG else android.util.Log.ERROR
            )
            .build()

    // -------------------------------------------------------------------------
    // Private helpers
    // -------------------------------------------------------------------------

    private fun initLogging() {
        if (BuildConfig.DEBUG) {
            // Debug: full stack-trace logging with class names
            Timber.plant(Timber.DebugTree())
        } else {
            // Release: only crash-worthy events — integrate with your crash reporter
            // e.g. Timber.plant(CrashlyticsTree())
            Timber.plant(ReleaseTree())
        }
    }
}

/**
 * ReleaseTree — a production Timber tree that suppresses VERBOSE/DEBUG/INFO logs.
 *
 * In a real project, forward ERROR/WTF to a crash reporting SDK (Crashlytics etc.).
 * Deliberately does NOT include device data in log messages to protect user privacy.
 */
private class ReleaseTree : Timber.Tree() {
    override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
        if (priority < android.util.Log.WARN) return
        // TODO: forward to crash reporting SDK
    }
}
