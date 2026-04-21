package com.aegis.agent.domain.usecase

import com.aegis.agent.data.scanner.DeviceScanner
import com.aegis.agent.domain.model.DeviceReport
import javax.inject.Inject

/**
 * CollectDeviceTelemetryUseCase — domain layer interactor for device posture collection.
 *
 * Encapsulates the single business operation of running a full device scan and
 * returning the structured [DeviceReport].  By sitting between the presentation /
 * worker layer and the data layer, it keeps [TelemetrySyncWorker] decoupled from
 * the concrete [DeviceScanner] implementation.
 *
 * ## Usage (inside a CoroutineWorker / ViewModel)
 * ```kotlin
 * val result: Result<DeviceReport> = collectDeviceTelemetryUseCase()
 * result.onSuccess { report ->
 *     telemetryRepository.upload(report)
 * }.onFailure { error ->
 *     Timber.e(error, "Device scan failed")
 * }
 * ```
 *
 * @param deviceScanner The data-layer scanner injected by Hilt.
 */
class CollectDeviceTelemetryUseCase @Inject constructor(
    private val deviceScanner: DeviceScanner,
) {

    /**
     * Executes the device scan and wraps the result in a [Result].
     *
     * Returns [Result.success] with the [DeviceReport] on success, or
     * [Result.failure] if [DeviceScanner.scan] throws (e.g., unexpected
     * security manager denial, OOM, etc.).
     *
     * All work is delegated to [DeviceScanner] which already switches to
     * the appropriate coroutine dispatcher — no extra [withContext] needed here.
     */
    suspend operator fun invoke(): Result<DeviceReport> =
        runCatching { deviceScanner.scan() }
}
