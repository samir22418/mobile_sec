package com.aegis.agent.data.system

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.aegis.agent.AegisSdk
import timber.log.Timber

/**
 * Handles system lifecycle broadcasts that can interrupt the WorkManager
 * schedule, such as device reboot or app package replacement.
 *
 * Agent configuration is restored from encrypted local storage when available,
 * so the schedule can be verified without waiting for the host app to call init.
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
        if (AegisSdk.initFromPersistedConfig(context.applicationContext)) {
            Timber.i("BootReceiver: AEGIS schedule restored from persisted config")
        } else {
            Timber.w("BootReceiver: no persisted AEGIS config available; schedule not restored")
        }
    }
}
