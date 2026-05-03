package com.aegis.agent.data.system

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.aegis.agent.AegisSdk
import com.aegis.agent.di.AgentConfigHolder
import timber.log.Timber

/**
 * Handles system lifecycle broadcasts that can interrupt the WorkManager
 * schedule, such as device reboot or app package replacement.
 *
 * Agent configuration is currently held in memory by AgentConfigHolder. This
 * receiver can therefore reschedule immediately only when the host app has
 * initialized AegisSdk in the current process. Persisted provisioning belongs
 * to the next backend/enrollment stage.
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED -> rescheduleIfConfigured(context)

            else -> Timber.d("BootReceiver: ignored action=${intent.action}")
        }
    }

    private fun rescheduleIfConfigured(context: Context) {
        val config = AgentConfigHolder.config
        if (config == null) {
            Timber.w(
                "BootReceiver: AEGIS config is not available yet; " +
                    "host Application must call AegisSdk.init()"
            )
            return
        }

        AegisSdk.init(context.applicationContext, config)
        Timber.i("BootReceiver: AEGIS schedule verified after system broadcast")
    }
}
