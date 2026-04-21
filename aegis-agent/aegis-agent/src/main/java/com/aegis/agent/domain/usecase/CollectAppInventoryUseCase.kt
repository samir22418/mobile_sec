package com.aegis.agent.domain.usecase

import com.aegis.agent.data.apps.AppIntelligenceCollector
import com.aegis.agent.domain.model.AppSnapshot
import javax.inject.Inject

/**
 * CollectAppInventoryUseCase — domain layer interactor for app inventory collection.
 *
 * Encapsulates the single business operation of running a full or delta app
 * inventory scan and returning the structured [AppSnapshot].  Keeping this logic
 * in a use case decouples [TelemetrySyncWorker] from the concrete
 * [AppIntelligenceCollector] implementation, making both independently testable.
 *
 * ## Delta behaviour
 * On the **first invocation** (no DataStore state) the returned [AppSnapshot]
 * contains every installed package and [AppSnapshot.isDelta] is `false`.
 * On **subsequent invocations** only apps that changed since the last scan are
 * included and [AppSnapshot.isDelta] is `true`.
 *
 * ## Usage
 * ```kotlin
 * val result: Result<AppSnapshot> = collectAppInventoryUseCase()
 * result.onSuccess { snapshot ->
 *     Timber.d("apps changed=${snapshot.apps.size} total=${snapshot.totalAppCount}")
 * }.onFailure { error ->
 *     Timber.e(error, "App inventory collection failed")
 * }
 * ```
 *
 * @param appIntelligenceCollector The data-layer collector injected by Hilt.
 */
class CollectAppInventoryUseCase @Inject constructor(
    private val appIntelligenceCollector: AppIntelligenceCollector,
) {

    /**
     * Executes the app inventory scan and wraps the result in a [Result].
     *
     * Returns [Result.success] with the [AppSnapshot] on success, or
     * [Result.failure] if [AppIntelligenceCollector.collect] throws (e.g.,
     * SecurityException from PackageManager, OOM, or DataStore I/O error).
     *
     * All work is delegated to [AppIntelligenceCollector] which dispatches to
     * [kotlinx.coroutines.Dispatchers.IO] internally — no extra context switch
     * required here.
     */
    suspend operator fun invoke(): Result<AppSnapshot> =
        runCatching { appIntelligenceCollector.collect() }
}
