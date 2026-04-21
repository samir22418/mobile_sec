package com.aegis.agent.di

import com.aegis.agent.data.logs.ImportanceFilter
import com.aegis.agent.data.logs.LogFilterAgent
import com.aegis.agent.data.logs.LogcatReader
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import javax.inject.Named
import javax.inject.Singleton

/**
 * LogModule — Hilt module that wires [LogFilterAgent] and its dependencies.
 *
 * ## Scope choice: SingletonComponent
 * The [LogFilterAgent] is a singleton because:
 * - It owns a continuously-running logcat reader process.
 * - The [kotlinx.coroutines.flow.MutableSharedFlow] backing [LogFilterAgent.filteredLogs]
 *   must be **shared** across all consumers (WorkerManager runs in the same process).
 * - Multiple instances would spawn multiple redundant `logcat` child processes.
 *
 * ## CoroutineScope strategy
 * We provide a dedicated `@Named("logAgentScope")` scope rather than injecting
 * the application coroutine scope directly, so the log agent's coroutines:
 * - Are isolated from the application's main scope cancellation.
 * - Use [SupervisorJob] so a crash in one coroutine (reader or flusher) does not
 *   propagate to the other.
 * - Run on [Dispatchers.Default] by default; the reader switches to [Dispatchers.IO]
 *   internally for the blocking logcat read.
 */
@Module
@InstallIn(SingletonComponent::class)
object LogModule {

    /**
     * Provides the dedicated [CoroutineScope] for the [LogFilterAgent].
     *
     * [SupervisorJob] ensures that if the reader coroutine fails unexpectedly,
     * the flusher coroutine remains alive, and vice versa.
     */
    @Provides
    @Singleton
    @Named("logAgentScope")
    fun provideLogAgentScope(): CoroutineScope =
        CoroutineScope(SupervisorJob() + Dispatchers.Default)

    /**
     * Provides the [LogcatReader] — stateless, singleton.
     *
     * The reader itself holds no state; only the `lines()` flow, when collected,
     * starts the underlying `logcat` process.
     */
    @Provides
    @Singleton
    fun provideLogcatReader(): LogcatReader = LogcatReader()

    /**
     * Provides the [ImportanceFilter] — stateless, singleton.
     *
     * Regex patterns are pre-compiled at construction, making this singleton
     * critical for performance (avoids re-compiling patterns on every scan cycle).
     */
    @Provides
    @Singleton
    fun provideImportanceFilter(): ImportanceFilter = ImportanceFilter()

    /**
     * Provides the fully-wired [LogFilterAgent].
     *
     * Note: [start] is **not** called here — the agent is started lazily by
     * [TelemetrySyncWorker] or, in a future phase, by a long-running
     * [android.app.Service] to ensure continuous monitoring.
     *
     * @param logcatReader Pre-compiled logcat reader.
     * @param filter       Pre-compiled importance filter.
     * @param deviceId     Named device ID from [ScannerModule].
     * @param scope        Dedicated supervisor scope from [provideLogAgentScope].
     */
    @Provides
    @Singleton
    fun provideLogFilterAgent(
        logcatReader: LogcatReader,
        filter: ImportanceFilter,
        @Named("deviceId")      deviceId: String,
        @Named("logAgentScope") scope: CoroutineScope,
    ): LogFilterAgent = LogFilterAgent(
        logcatReader = logcatReader,
        filter       = filter,
        deviceId     = deviceId,
        scope        = scope,
    )
}
