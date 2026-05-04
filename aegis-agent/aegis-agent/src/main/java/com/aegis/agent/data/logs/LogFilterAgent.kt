package com.aegis.agent.data.logs

import com.aegis.agent.domain.model.ImportantLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import timber.log.Timber
import java.util.concurrent.atomic.AtomicLong
import javax.inject.Inject
import javax.inject.Named

/**
 * LogFilterAgent — the central orchestrator for real-time security log monitoring.
 *
 * ## Responsibilities
 * 1. **Ingest:** Receives a continuous stream of raw logcat lines from [LogcatReader].
 * 2. **Filter:** Passes each line through [ImportanceFilter]; discards non-matching lines
 *    **immediately** — they are never stored, buffered, or logged.
 * 3. **Buffer:** Retains matching lines in a bounded in-memory queue (max [BUFFER_MAX_SIZE]
 *    entries).  Entries older than [BUFFER_TTL_MS] are evicted on each flush cycle.
 * 4. **Flush:** Emits the buffer contents via [filteredLogs] on a schedule:
 *    - Every [FLUSH_INTERVAL_MS] seconds (30 s by default), **or**
 *    - Immediately when the buffer reaches [FLUSH_THRESHOLD] entries (≥ 50), whichever
 *      comes first.
 *
 * ## Architecture
 * ```
 * logcat process
 *       │  Flow<RawLogLine>
 *       ▼
 * LogcatReader.lines()
 *       │
 *       ▼
 * ImportanceFilter.evaluate()  ──── DISCARD (null) ─────────────────────────X
 *       │ FilterResult (non-null)
 *       ▼
 *   in-memory buffer  (ArrayDeque, max 200, TTL 10 min)
 *       │ on timer OR threshold hit
 *       ▼
 * MutableSharedFlow<List<ImportantLog>>  ──▶  collector (Worker / Upload)
 * ```
 *
 * ## Thread safety
 * All buffer mutations are protected by [bufferMutex].  The logcat reader and the
 * periodic flusher run in separate coroutines; both modify the shared buffer only
 * after acquiring the mutex.
 *
 * ## Lifecycle
 * Call [start] to begin monitoring.  Call [stop] to cancel all coroutines and
 * clear the buffer.  [start] is idempotent — calling it twice does nothing.
 *
 * @param logcatReader  Source of raw parsed logcat lines.
 * @param filter        Stateless importance classifier.
 * @param deviceId      AEGIS device identifier embedded in every [ImportantLog].
 * @param scope         [CoroutineScope] that owns the agent's coroutines.
 *                      Pass `ProcessLifecycleOwner.lifecycleScope` or a custom
 *                      scope created with [SupervisorJob] + [Dispatchers.Default].
 */
class LogFilterAgent @Inject constructor(
    private val logcatReader: LogcatReader,
    private val filter: ImportanceFilter,
    @Named("deviceId") private val deviceId: String,
    @Named("logAgentScope") private val scope: CoroutineScope,
) {

    // =========================================================================
    // State
    // =========================================================================

    /** Guards all mutations to [buffer]. */
    private val bufferMutex = Mutex()

    /**
     * In-memory log buffer.  Bounded to [BUFFER_MAX_SIZE] entries; excess entries
     * cause the oldest entry to be dropped (oldest-first eviction policy).
     */
    private val buffer = ArrayDeque<ImportantLog>(BUFFER_MAX_SIZE)

    /** Monotonically-increasing ID counter for [ImportantLog.id]. */
    private val idCounter = AtomicLong(0L)

    /** Backing field for the public [filteredLogs] flow. */
    private val _filteredLogs = MutableSharedFlow<List<ImportantLog>>(
        replay          = 0,       // Hot flow — no replay; late subscribers miss old batches
        extraBufferCapacity = 8,   // Prevents suspension if the collector is briefly slow
    )

    // Active coroutine jobs — tracked for cancellation in [stop]
    private var readerJob: Job? = null
    private var flusherJob: Job? = null

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * A hot [Flow] that emits a batch ([List]) of [ImportantLog] entries whenever
     * the buffer is flushed.
     *
     * ## Flush triggers
     * - **Timer:** Every [FLUSH_INTERVAL_MS] (30 seconds).
     * - **Threshold:** Immediately when the buffer reaches [FLUSH_THRESHOLD] (50 entries).
     *
     * ## Subscriber behaviour
     * - This is a **hot** SharedFlow with no replay.  Subscribers that start
     *   collecting after a flush will miss that batch.
     * - If [start] has not been called, no emissions will occur.
     *
     * ```kotlin
     * logFilterAgent.filteredLogs
     *     .onEach { batch -> uploadTelemetry(batch) }
     *     .launchIn(applicationScope)
     * ```
     */
    val filteredLogs: Flow<List<ImportantLog>> = _filteredLogs.asSharedFlow()

    /**
     * Starts logcat monitoring and the periodic flush cycle.
     *
     * Launches two coroutines in [scope]:
     * 1. **Reader coroutine:** continuously reads [LogcatReader.lines], filters,
     *    and appends to the buffer.
     * 2. **Flusher coroutine:** wakes every [FLUSH_INTERVAL_MS] to emit batches.
     *
     * Idempotent — calling [start] on a running agent does nothing.
     */
    fun start() {
        if (readerJob?.isActive == true) {
            Timber.d("LogFilterAgent: already running — ignoring duplicate start()")
            return
        }

        Timber.i("LogFilterAgent: starting")

        // Coroutine 1: Logcat reader → filter → buffer
        readerJob = scope.launch {
            logcatReader.lines().collect { rawLine ->
                val result = filter.evaluate(rawLine.tag, rawLine.level, rawLine.message)
                    ?: return@collect   // Discard — never touch buffer for misses

                val log = ImportantLog(
                    id               = idCounter.incrementAndGet(),
                    timestampEpochMs = System.currentTimeMillis(),
                    deviceId         = deviceId,
                    tag              = rawLine.tag,
                    level            = rawLine.level,
                    message          = rawLine.message,
                    matchedRule      = result.matchedRule,
                )

                bufferMutex.withLock {
                    // Enforce max buffer size — drop oldest if full
                    if (buffer.size >= BUFFER_MAX_SIZE) {
                        buffer.removeFirst()
                        Timber.w("LogFilterAgent: buffer full — oldest entry evicted")
                    }
                    buffer.addLast(log)
                }

                // Immediate flush if threshold reached
                if (buffer.size >= FLUSH_THRESHOLD) {
                    Timber.d("LogFilterAgent: threshold reached — flushing early")
                    flushBuffer()
                }
            }
        }

        // Coroutine 2: Periodic flush timer
        flusherJob = scope.launch {
            while (isActive) {
                delay(FLUSH_INTERVAL_MS)
                flushBuffer()
            }
        }
    }

    /**
     * Stops the logcat reader and flush timer, clears the in-memory buffer,
     * and resets the ID counter.
     *
     * After calling [stop], [start] may be called again to restart monitoring.
     */
    fun stop() {
        Timber.i("LogFilterAgent: stopping")
        readerJob?.cancel()
        flusherJob?.cancel()
        readerJob  = null
        flusherJob = null
        buffer.clear()
        idCounter.set(0L)
    }

    /**
     * Exposes the current number of buffered log entries.
     *
     * Useful for health checks and instrumentation tests.
     */
    suspend fun bufferedCount(): Int = bufferMutex.withLock { buffer.size }

    /**
     * Starts a short worker-scoped log collection window and returns a bounded
     * snapshot of important logs.
     *
     * This is the POC lifecycle used by [TelemetrySyncWorker]: collect around a
     * scan run, persist the selected lines with that scan, then stop the reader.
     * A future enterprise build can keep [start] running from a service instead.
     */
    suspend fun collectSnapshot(
        windowMs: Long = SNAPSHOT_WINDOW_MS,
        maxEntries: Int = SNAPSHOT_MAX_SIZE,
    ): List<ImportantLog> = coroutineScope {
        val collected = mutableListOf<ImportantLog>()
        val collectorJob = launch {
            filteredLogs.collect { batch ->
                val remaining = maxEntries - collected.size
                if (remaining > 0) {
                    collected += batch.take(remaining)
                }
            }
        }

        try {
            start()
            delay(windowMs)
            val remaining = maxEntries - collected.size
            if (remaining > 0) {
                collected += drainBuffer(remaining)
            }
            collected.toList()
        } finally {
            collectorJob.cancel()
            stop()
        }
    }

    // =========================================================================
    // Internal flush logic
    // =========================================================================

    /**
     * Drains the buffer, evicts stale entries (older than [BUFFER_TTL_MS]),
     * and emits a non-empty batch to [filteredLogs].
     *
     * This function is **mutex-protected** — concurrent calls from the reader
     * coroutine (threshold flush) and the flusher coroutine (timer flush) are
     * serialised safely.
     */
    internal suspend fun flushBuffer() {
        val batch = drainBuffer(maxEntries = Int.MAX_VALUE)

        if (batch.isNotEmpty()) {
            Timber.i("LogFilterAgent: flushing ${batch.size} log entries")
            _filteredLogs.emit(batch)
        }
    }

    private suspend fun drainBuffer(maxEntries: Int): List<ImportantLog> =
        bufferMutex.withLock {
            if (buffer.isEmpty() || maxEntries <= 0) return@withLock emptyList()

            val cutoffMs = System.currentTimeMillis() - BUFFER_TTL_MS
            buffer.removeAll { log -> log.timestampEpochMs < cutoffMs }

            if (buffer.isEmpty()) return@withLock emptyList()

            val batchSize = minOf(maxEntries, buffer.size)
            buildList(batchSize) {
                repeat(batchSize) {
                    add(buffer.removeFirst())
                }
            }
        }

    // =========================================================================
    // Constants
    // =========================================================================

    companion object {
        /** Maximum number of entries in the in-memory buffer before oldest-first eviction. */
        const val BUFFER_MAX_SIZE   = 200

        /** Minimum buffer size that triggers an immediate early flush. */
        const val FLUSH_THRESHOLD   = 50

        /** Wall-clock interval between scheduled buffer flushes (30 seconds). */
        const val FLUSH_INTERVAL_MS = 30_000L

        /** Maximum age of a buffered entry before it is evicted on next flush (10 minutes). */
        const val BUFFER_TTL_MS     = 10 * 60 * 1_000L   // 10 minutes in milliseconds

        /** Short worker-scoped capture window used by telemetry scans. */
        const val SNAPSHOT_WINDOW_MS = 2_000L

        /** Maximum logs attached to one telemetry payload. */
        const val SNAPSHOT_MAX_SIZE = 50
    }
}
