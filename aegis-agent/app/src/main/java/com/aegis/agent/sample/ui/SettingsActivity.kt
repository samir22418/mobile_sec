package com.aegis.agent.sample.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.aegis.agent.AegisSdk
import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.AgentConfig
import com.aegis.agent.sample.BuildConfig
import com.aegis.agent.sample.R
import com.aegis.agent.sample.databinding.ActivitySettingsBinding
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import javax.inject.Inject

@AndroidEntryPoint
class SettingsActivity : AppCompatActivity() {

    @Inject
    lateinit var scanResultRepository: ScanResultRepository

    @Inject
    lateinit var configRepository: ConfigRepository

    private lateinit var binding: ActivitySettingsBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnBack.setOnClickListener { finish() }
        binding.btnSaveConnection.setOnClickListener { saveConnection() }
        binding.btnTestConnection.setOnClickListener { testConnection() }

        renderConfig(configRepository.load() ?: defaultConfig())

        lifecycleScope.launch {
            scanResultRepository.observeLatest().collect { record ->
                binding.txtLatestPayload.text = record?.payloadId ?: "--"
                binding.txtLatestUpload.text = record?.uploadStatus?.name ?: "--"
            }
        }
    }

    private fun renderConfig(config: AgentConfig) {
        binding.editBackendUrl.setText(config.backendUrl)
        binding.editDeviceId.setText(config.deviceId)
        binding.editEnrollmentToken.setText(config.enrollmentToken)
        binding.txtConnectionStatus.text = "Saved device: ${config.deviceId}"
        binding.txtConnectionStatus.setTextColor(color(R.color.text_muted))
    }

    private fun saveConnection() {
        val config = readFormConfig() ?: return
        if (!configRepository.save(config)) {
            showStatus("Could not save connection settings", isError = true)
            return
        }

        AegisSdk.init(applicationContext, config)
        showStatus("Saved. Device will report as ${config.deviceId}", isError = false)
    }

    private fun testConnection() {
        val config = readFormConfig() ?: return
        setButtonsEnabled(false)
        showStatus("Testing backend connection...", isError = false)

        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching {
                    val connection = URL("${config.backendUrl}/health").openConnection() as HttpURLConnection
                    connection.requestMethod = "GET"
                    connection.connectTimeout = 5000
                    connection.readTimeout = 5000
                    connection.setRequestProperty("Authorization", "Bearer ${config.enrollmentToken}")
                    val code = connection.responseCode
                    connection.disconnect()
                    if (code !in 200..299) {
                        throw IllegalStateException("Backend returned HTTP $code")
                    }
                }
            }

            setButtonsEnabled(true)
            if (result.isSuccess) {
                showStatus("Connection OK. Save, then run a scan.", isError = false)
            } else {
                val message = result.exceptionOrNull()?.message ?: "Connection failed"
                showStatus(message, isError = true)
            }
        }
    }

    private fun readFormConfig(): AgentConfig? {
        clearErrors()

        val backendUrl = normalizeBackendUrl(binding.editBackendUrl.text?.toString().orEmpty())
        val deviceId = binding.editDeviceId.text?.toString()?.trim().orEmpty()
        val token = binding.editEnrollmentToken.text?.toString()?.trim().orEmpty()

        var isValid = true
        if (!isValidBackendUrl(backendUrl)) {
            binding.inputBackendUrl.error = "Use http://host:port or https://host"
            isValid = false
        }
        if (deviceId.isBlank()) {
            binding.inputDeviceId.error = "Device ID is required"
            isValid = false
        }
        if (token.isBlank()) {
            binding.inputEnrollmentToken.error = "Enrollment token is required"
            isValid = false
        }
        if (!isValid) {
            showStatus("Fix the highlighted fields", isError = true)
            return null
        }

        return AgentConfig(
            backendUrl = backendUrl,
            deviceId = deviceId,
            enrollmentToken = token,
            isByodMode = false,
            scanIntervalMin = 60L,
        )
    }

    private fun normalizeBackendUrl(value: String): String {
        val trimmed = value.trim().trimEnd('/')
        return if (trimmed.endsWith("/api/v1")) {
            trimmed.removeSuffix("/api/v1")
        } else {
            trimmed
        }
    }

    private fun isValidBackendUrl(value: String): Boolean =
        runCatching {
            val uri = URI(value)
            uri.scheme in setOf("http", "https") && !uri.host.isNullOrBlank()
        }.getOrDefault(false)

    private fun clearErrors() {
        binding.inputBackendUrl.error = null
        binding.inputDeviceId.error = null
        binding.inputEnrollmentToken.error = null
    }

    private fun defaultConfig(): AgentConfig =
        AgentConfig(
            backendUrl = normalizeBackendUrl(BuildConfig.AEGIS_BACKEND_URL),
            deviceId = "sample-device-001",
            enrollmentToken = "sample-token",
            isByodMode = false,
            scanIntervalMin = 60L,
        )

    private fun showStatus(message: String, isError: Boolean) {
        binding.txtConnectionStatus.text = message
        binding.txtConnectionStatus.setTextColor(
            color(if (isError) R.color.status_danger else R.color.status_good)
        )
    }

    private fun setButtonsEnabled(enabled: Boolean) {
        binding.btnSaveConnection.isEnabled = enabled
        binding.btnTestConnection.isEnabled = enabled
    }

    private fun color(id: Int): Int = androidx.core.content.ContextCompat.getColor(this, id)
}
