package com.aegis.agent.di

import android.content.Context
import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.data.scanner.DeviceScanner
import com.aegis.agent.data.scanner.RootDetector
import com.aegis.agent.domain.model.AgentConfig
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Named
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object ScannerModule {

    @Provides
    @Singleton
    fun provideRootDetector(): RootDetector = RootDetector()

    @Provides
    @Named("deviceId")
    fun provideDeviceId(
        configRepository: ConfigRepository,
    ): String =
        AgentConfigHolder.getOrLoad(configRepository)?.deviceId ?: "unprovisioned"

    @Provides
    @Singleton
    fun provideDeviceScanner(
        @ApplicationContext context: Context,
        rootDetector: RootDetector,
        @Named("deviceId") deviceId: String,
    ): DeviceScanner = DeviceScanner(
        context = context,
        rootDetector = rootDetector,
        deviceId = deviceId,
    )
}

object AgentConfigHolder {
    @Volatile
    var config: AgentConfig? = null

    fun getOrLoad(configRepository: ConfigRepository): AgentConfig? {
        config?.let { return it }
        return configRepository.load()?.also { config = it }
    }
}
