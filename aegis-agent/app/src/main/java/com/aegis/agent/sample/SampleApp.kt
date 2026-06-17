package com.aegis.agent.sample

import com.aegis.agent.AegisApplication
import com.aegis.agent.AegisSdk
import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.domain.model.AgentConfig
import dagger.hilt.android.HiltAndroidApp
import timber.log.Timber

@HiltAndroidApp
class SampleApp : AegisApplication() {

    override fun onCreate() {
        super.onCreate()

        val configRepository = ConfigRepository(this)
        val config = configRepository.load() ?: AgentConfig(
            backendUrl = BuildConfig.AEGIS_BACKEND_URL,
            deviceId = "sample-device-001",
            enrollmentToken = "sample-token",
            isByodMode = false,
            scanIntervalMin = 60L,
        )

        AegisSdk.init(
            context = this,
            config = config,
        )
        Timber.d("SampleApp: AEGIS agent initialised for device=${config.deviceId}")
    }
}
