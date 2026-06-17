package com.aegis.agent.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import com.aegis.agent.data.apps.AppIntelligenceCollector
import com.aegis.agent.data.persistence.ConfigRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Named
import javax.inject.Singleton

// ---------------------------------------------------------------------------
// Top-level DataStore delegate — one per process; name must be unique.
// Declared at file scope (outside any class) as required by the DataStore API.
// ---------------------------------------------------------------------------
private val Context.appInventoryDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "aegis_app_inventory"
)

/**
 * AppModule — Hilt module that provides [AppIntelligenceCollector] and its
 * [DataStore] dependency.
 *
 * ## DataStore Naming
 * The file `aegis_app_inventory` is stored in the app's private data directory
 * (`/data/data/<package>/files/datastore/aegis_app_inventory.preferences_pb`).
 * It is separate from any other DataStore instances used by the host app to
 * prevent key collisions.
 *
 * ## isByodMode binding
 * The BYOD flag is read from [AgentConfigHolder] or encrypted persisted config,
 * mirroring the same pattern used by [ScannerModule] for deviceId.
 */
@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    /**
     * Provides a singleton [DataStore] instance scoped to the AEGIS app inventory.
     *
     * The `preferencesDataStore` delegate guarantees a single instance per named
     * store — this provider simply exposes it into the Hilt graph.
     *
     * @param context Application context from Hilt.
     * @return The [DataStore] used by [AppIntelligenceCollector].
     */
    @Provides
    @Singleton
    fun provideAppInventoryDataStore(
        @ApplicationContext context: Context,
    ): DataStore<Preferences> = context.appInventoryDataStore

    /**
     * Provides the BYOD mode flag from [AgentConfigHolder].
     *
     * `@Named("isByodMode")` prevents collision with other Boolean bindings
     * in the Hilt graph.
     */
    @Provides
    @Named("isByodMode")
    fun provideIsByodMode(
        configRepository: ConfigRepository,
    ): Boolean =
        AgentConfigHolder.getOrLoad(configRepository)?.isByodMode ?: false

    /**
     * Provides the fully-wired [AppIntelligenceCollector] as a singleton.
     *
     * A singleton is appropriate because:
     * - The DataStore must not be duplicated (would cause concurrent write issues).
     * - [AppIntelligenceCollector.packageEvents] is a long-lived flow shared
     *   across the worker and any future consumers.
     *
     * @param context      Application context.
     * @param dataStore    The inventory [DataStore].
     * @param deviceId     Named device identifier.
     * @param isByodMode   Named BYOD flag.
     * @return The singleton [AppIntelligenceCollector].
     */
    @Provides
    @Singleton
    fun provideAppIntelligenceCollector(
        @ApplicationContext context: Context,
        dataStore: DataStore<Preferences>,
        @Named("deviceId")   deviceId: String,
        @Named("isByodMode") isByodMode: Boolean,
    ): AppIntelligenceCollector = AppIntelligenceCollector(
        context     = context,
        dataStore   = dataStore,
        deviceId    = deviceId,
        isByodMode  = isByodMode,
    )
}
