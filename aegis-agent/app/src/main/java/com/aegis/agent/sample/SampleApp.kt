package com.aegis.agent.sample

import com.aegis.agent.AegisApplication
import com.aegis.agent.AegisSdk
import com.aegis.agent.domain.model.AgentConfig
import dagger.hilt.android.HiltAndroidApp
import timber.log.Timber

/**
 * SampleApp — demonstrates how a host application initialises the AEGIS agent.
 *
 * Extends [AegisApplication] so Hilt and WorkManager are already wired.
 * Simply call [AegisSdk.init] with your runtime config in [onCreate].
 */
@HiltAndroidApp
class SampleApp : AegisApplication() {

    override fun onCreate() {
        super.onCreate()

        // Initialise AEGIS with placeholder config — replace with real values
        AegisSdk.init(
            context = this,
            config = AgentConfig(
                backendUrl      = BuildConfig.AEGIS_BACKEND_URL,
                deviceId        = "sample-device-001",
                enrollmentToken = "sample-token",
                isByodMode      = false,
                scanIntervalMin = 60L,
                cloudProjectNumber = BuildConfig.AEGIS_CLOUD_PROJECT_NUMBER,
            )
        )
        Timber.d("SampleApp: AEGIS agent initialised")
    }
}
