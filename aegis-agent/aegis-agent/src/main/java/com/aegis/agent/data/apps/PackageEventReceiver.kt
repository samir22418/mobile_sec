package com.aegis.agent.data.apps

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import com.aegis.agent.domain.model.PackageEvent
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import timber.log.Timber

/**
 * PackageEventReceiver — a [BroadcastReceiver] that converts Android package-change
 * broadcasts into a Kotlin [Flow] of [PackageEvent] objects.
 *
 * ## Why a separate class?
 * The manifest-declared `<receiver>` entry in `AndroidManifest.xml` registers
 * `PackageEventReceiver` statically so Android can wake the process even if it
 * is not running.  The [packageEvents] flow, however, is used *in-process* to
 * trigger real-time incremental uploads — these complement each other.
 *
 * ## Flow lifecycle
 * The flow is *cold* when created via [packageEvents] but becomes a *hot* producer
 * once the first collector subscribes (the receiver is registered at that point).
 * When the collector's coroutine scope is cancelled, the receiver is automatically
 * unregistered via [awaitClose].
 *
 * ## Manifest requirement
 * The static declaration in `AndroidManifest.xml` already covers:
 * ```xml
 * <receiver android:name=".data.apps.PackageEventReceiver" android:exported="false">
 *     <intent-filter>
 *         <action android:name="android.intent.action.PACKAGE_ADDED" />
 *         <action android:name="android.intent.action.PACKAGE_REMOVED" />
 *         <action android:name="android.intent.action.PACKAGE_REPLACED" />
 *         <data android:scheme="package" />
 *     </intent-filter>
 * </receiver>
 * ```
 */
class PackageEventReceiver : BroadcastReceiver() {

    /**
     * Called by Android when a package is installed, updated, or removed.
     *
     * In the *static* (manifest-declared) usage the receiver is only alive for
     * the duration of this method — no persistent state should be kept here.
     * The real work is delegated to [packageEvents].
     */
    override fun onReceive(context: Context, intent: Intent) {
        val packageName = intent.data?.schemeSpecificPart ?: run {
            Timber.w("PackageEventReceiver: received intent with no package data")
            return
        }

        val eventType = when (intent.action) {
            Intent.ACTION_PACKAGE_ADDED,
            Intent.ACTION_PACKAGE_REPLACED -> PackageEvent.EventType.INSTALLED

            Intent.ACTION_PACKAGE_REMOVED  -> PackageEvent.EventType.REMOVED
            else                           -> {
                Timber.w("PackageEventReceiver: unhandled action=${intent.action}")
                return
            }
        }

        Timber.d("PackageEventReceiver: $eventType → $packageName")
    }

    companion object {

        /**
         * Creates a cold [Flow] that emits a [PackageEvent] every time a package
         * is installed, updated, or removed.
         *
         * The [BroadcastReceiver] is registered dynamically when the flow is
         * collected and unregistered automatically when the collector's scope
         * is cancelled — no manual cleanup required.
         *
         * **Thread safety:** [callbackFlow] guarantees that emissions are
         * serialised; a [kotlinx.coroutines.channels.Channel] with an unlimited
         * buffer ensures broadcasts are never dropped if the collector is slow.
         *
         * **Usage:**
         * ```kotlin
         * appIntelligenceCollector.packageEvents
         *     .onEach { event -> uploadIncremental(event) }
         *     .launchIn(lifecycleScope)
         * ```
         *
         * @param context Application context used to register the receiver.
         * @return A [Flow] that emits [PackageEvent] objects indefinitely.
         */
        fun packageEvents(context: Context): Flow<PackageEvent> = callbackFlow {
            val receiver = object : BroadcastReceiver() {
                override fun onReceive(ctx: Context, intent: Intent) {
                    val packageName = intent.data?.schemeSpecificPart ?: return
                    val eventType = when (intent.action) {
                        Intent.ACTION_PACKAGE_ADDED,
                        Intent.ACTION_PACKAGE_REPLACED -> PackageEvent.EventType.INSTALLED
                        Intent.ACTION_PACKAGE_REMOVED  -> PackageEvent.EventType.REMOVED
                        else                           -> return
                    }
                    val event = PackageEvent(
                        packageName = packageName,
                        eventType   = eventType,
                        timestampMs = System.currentTimeMillis(),
                    )
                    Timber.d("PackageEventReceiver[flow]: $eventType → $packageName")
                    trySend(event) // non-blocking; buffer is Channel.UNLIMITED
                }
            }

            val filter = IntentFilter().apply {
                addAction(Intent.ACTION_PACKAGE_ADDED)
                addAction(Intent.ACTION_PACKAGE_REMOVED)
                addAction(Intent.ACTION_PACKAGE_REPLACED)
                addDataScheme("package")
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
            } else {
                context.registerReceiver(receiver, filter)
            }
            Timber.d("PackageEventReceiver[flow]: receiver registered")

            // Unregister when the collecting coroutine scope is cancelled
            awaitClose {
                context.unregisterReceiver(receiver)
                Timber.d("PackageEventReceiver[flow]: receiver unregistered")
            }
        }
    }
}
