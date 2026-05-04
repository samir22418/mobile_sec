package com.aegis.agent.sample.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.sample.BuildConfig
import com.aegis.agent.sample.databinding.ActivitySettingsBinding
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class SettingsActivity : AppCompatActivity() {

    @Inject
    lateinit var scanResultRepository: ScanResultRepository

    private lateinit var binding: ActivitySettingsBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnBack.setOnClickListener { finish() }
        binding.txtBackendUrl.text = BuildConfig.AEGIS_BACKEND_URL
        binding.txtEnrollmentStatus.text = "Sample token configured"

        lifecycleScope.launch {
            scanResultRepository.observeLatest().collect { record ->
                binding.txtDeviceId.text = record?.deviceId ?: "sample-device-001"
                binding.txtLatestPayload.text = record?.payloadId ?: "--"
                binding.txtLatestUpload.text = record?.uploadStatus?.name ?: "--"
            }
        }
    }
}
