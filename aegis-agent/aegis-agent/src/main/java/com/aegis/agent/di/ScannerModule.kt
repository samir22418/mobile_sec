package com.aegis.agent.di

import android.content.Context
import com.aegis.agent.data.scanner.DeviceScanner
import com.aegis.agent.data.scanner.IntegrityApiClient
import com.aegis.agent.data.scanner.RootDetector
import com.aegis.agent.domain.model.AgentConfig
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Named
import javax.inject.Singleton

/**
 * ScannerModule — Hilt module that wires [DeviceScanner] and its dependencies.
 *
 * Placed in [SingletonComponent] so only one scanner exists per process lifetime,
 * matching the WorkManager cadence (a single worker calls [DeviceScanner.scan]
 * once per interval and reuses the same instance).
 *
 * **How to provide AgentConfig values:**
 * The [AgentConfig] is passed to [AegisSdk.init] at runtime, but Hilt modules are
 * static.  We bridge the gap by storing the config in a [AgentConfigHolder] singleton
 * that is populated during [AegisSdk.init].  The `@Named` bindings read from there.
 *
 * For the initial scaffold we use default / placeholder values.  Replace
 * [AgentConfigHolder.config] injection with a runtime-provisioned source once the
 * MDM integration layer (Prompt 2.x) is in place.
 */
@Module
@InstallIn(SingletonComponent::class)
object ScannerModule {

    /**
     * Provides the [RootDetector] — stateless, singleton.
     */
    @Provides
    @Singleton
    fun provideRootDetector(): RootDetector = RootDetector()

    /**
     * Provides the [IntegrityApiClient].
     *
     * The [cloudProjectNumber] must be the numeric Google Cloud project number
     * linked to your app in the Play Console.  Pass it via [AgentConfig] and
     * expose through [AgentConfigHolder].
     *
     * Placeholder value `0L` here — replace with the real number before shipping.
     */
    @Provides
    @Singleton
    fun provideIntegrityApiClient(
        @ApplicationContext context: Context,
        @Named("cloudProjectNumber") cloudProjectNumber: Long,
    ): IntegrityApiClient = IntegrityApiClient(
        context = context,
        cloudProjectNumber = cloudProjectNumber,
    )

    /**
     * Provides the cloud project number from [AgentConfigHolder].
     *
     * Using [Named] so this Long doesn't collide with other Long bindings.
     */
    @Provides
    @Named("cloudProjectNumber")
    fun provideCloudProjectNumber(): Long =
        AgentConfigHolder.config?.cloudProjectNumber ?: 0L

    /**
     * Provides the device ID from [AgentConfigHolder].
     *
     * Using [Named] to disambiguate from other String bindings.
     */
    @Provides
    @Named("deviceId")
    fun provideDeviceId(): String =
        AgentConfigHolder.config?.deviceId ?: "unprovisioned"

    /**
     * Provides the fully-wired [DeviceScanner].
     */
    @Provides
    @Singleton
    fun provideDeviceScanner(
        @ApplicationContext context: Context,
        rootDetector: RootDetector,
        integrityApiClient: IntegrityApiClient,
        @Named("deviceId") deviceId: String,
    ): DeviceScanner = DeviceScanner(
        context = context,
        rootDetector = rootDetector,
        integrityApiClient = integrityApiClient,
        deviceId = deviceId,
    )
}

/**
 * AgentConfigHolder — a simple thread-safe holder for the runtime [AgentConfig].
 *
 * Populated by [AegisSdk.init] before any Hilt-managed component first requests
 * a [DeviceScanner].  Using `@Volatile` ensures visibility across threads
 * without the overhead of a full lock.
 *
 * Extend with a proper datastore or DI-aware provisioning source in Phase 2.
 */
object AgentConfigHolder {
    @Volatile
    var config: AgentConfig? = null
}
