@file:Suppress("DEPRECATION")

package com.aegis.agent.data.persistence

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.aegis.agent.domain.model.AgentConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.serialization.SerializationException
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Persists the runtime AEGIS configuration across process death and reboot.
 *
 * The enrollment token is sensitive, so the payload is stored in
 * EncryptedSharedPreferences rather than plain SharedPreferences or DataStore.
 * Reads are synchronous because Hilt provider methods and BroadcastReceivers
 * need config before they can safely schedule or create agent components.
 */
@Singleton
class ConfigRepository @Inject constructor(
    @ApplicationContext
    private val context: Context,
) {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun save(config: AgentConfig): Boolean {
        val encoded = json.encodeToString(config)
        return runCatching {
            preferences()
                .edit()
                .putString(KEY_AGENT_CONFIG, encoded)
                .commit()
        }.onFailure { error ->
            Timber.e(error, "ConfigRepository: failed to persist AgentConfig")
        }.getOrDefault(false)
    }

    fun load(): AgentConfig? =
        runCatching {
            val encoded = preferences().getString(KEY_AGENT_CONFIG, null)
                ?: return@runCatching null
            json.decodeFromString<AgentConfig>(encoded)
        }.onFailure { error ->
            when (error) {
                is SerializationException,
                is IllegalArgumentException,
                is SecurityException -> Timber.e(error, "ConfigRepository: stored AgentConfig is unreadable")
                else -> Timber.e(error, "ConfigRepository: failed to load AgentConfig")
            }
        }.getOrNull()

    fun clear(): Boolean =
        runCatching {
            preferences()
                .edit()
                .remove(KEY_AGENT_CONFIG)
                .commit()
        }.onFailure { error ->
            Timber.e(error, "ConfigRepository: failed to clear AgentConfig")
        }.getOrDefault(false)

    private fun preferences() =
        EncryptedSharedPreferences.create(
            context.applicationContext,
            PREFS_NAME,
            masterKey(),
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )

    private fun masterKey(): MasterKey =
        MasterKey.Builder(context.applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

    companion object {
        private const val PREFS_NAME = "aegis_agent_config"
        private const val KEY_AGENT_CONFIG = "agent_config_json"
    }
}
