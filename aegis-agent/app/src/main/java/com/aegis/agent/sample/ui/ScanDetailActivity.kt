package com.aegis.agent.sample.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.sample.databinding.ActivityScanDetailBinding
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import java.text.DateFormat
import java.util.Date
import javax.inject.Inject

@AndroidEntryPoint
class ScanDetailActivity : AppCompatActivity() {

    @Inject
    lateinit var scanResultRepository: ScanResultRepository

    private lateinit var binding: ActivityScanDetailBinding
    private val prettyJson = Json {
        prettyPrint = true
        ignoreUnknownKeys = true
        encodeDefaults = true
    }
    private val dateFormat: DateFormat by lazy {
        DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT)
    }
    private var currentRecord: ScanRecord? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val scanId = intent.getLongExtra(EXTRA_SCAN_ID, MISSING_SCAN_ID)
        binding.btnBack.setOnClickListener { finish() }
        binding.btnCopyPayload.setOnClickListener { copyPayloadSummary() }
        binding.btnCopyAnalystBrief.setOnClickListener { copyAnalystBrief() }
        binding.btnShareAnalystBrief.setOnClickListener { shareAnalystBrief() }
        binding.btnToggleDeviceJson.setOnClickListener {
            toggleJson(binding.deviceJsonContainer, binding.btnToggleDeviceJson, "Device JSON")
        }
        binding.btnToggleAppsJson.setOnClickListener {
            toggleJson(binding.appsJsonContainer, binding.btnToggleAppsJson, "App JSON")
        }
        binding.btnToggleLogsJson.setOnClickListener {
            toggleJson(binding.logsJsonContainer, binding.btnToggleLogsJson, "Logs JSON")
        }
        binding.btnCopyDeviceJson.setOnClickListener {
            copyText("Device report JSON", currentRecord?.deviceReportJson.orEmpty())
        }
        binding.btnCopyAppsJson.setOnClickListener {
            copyText("App snapshot JSON", currentRecord?.appSnapshotJson.orEmpty())
        }
        binding.btnCopyLogsJson.setOnClickListener {
            copyText("Important logs JSON", currentRecord?.importantLogsJson.orEmpty())
        }

        if (scanId == MISSING_SCAN_ID) {
            renderMissing()
            return
        }

        lifecycleScope.launch {
            scanResultRepository.observeById(scanId).collect { record ->
                currentRecord = record
                render(record)
            }
        }
    }

    private fun render(record: ScanRecord?) {
        if (record == null) {
            renderMissing()
            return
        }

        binding.txtTitle.text = "Scan #${record.id}"
        binding.txtSubtitle.text = "${record.status.name} / ${record.trigger.name.lowercase()}"
        val brief = RiskBrief.from(record)
        binding.txtRiskScore.text = brief.score.toString()
        binding.txtRiskLabel.text = brief.label
        binding.txtRiskHeadline.text = brief.headline
        binding.txtRiskReasons.text = brief.reasonText
        binding.txtPayloadId.text = record.payloadId ?: "--"
        binding.txtUploadStatus.text = record.uploadStatus.name
        binding.txtRetryCount.text = record.retryCount.toString()
        binding.txtLastAttempt.text = formatTime(record.lastUploadAttemptAtEpochMs)
        binding.txtUploadedAt.text = formatTime(record.uploadedAtEpochMs)
        binding.txtUploadError.text = record.lastUploadError ?: "None"
        binding.txtStartedAt.text = formatTime(record.startedAtEpochMs)
        binding.txtCompletedAt.text = formatTime(record.completedAtEpochMs)
        binding.txtDeviceId.text = record.deviceId ?: "--"
        binding.txtRooted.text = record.isRooted?.toString() ?: "--"
        binding.txtIntegrity.text = "--"
        binding.txtPatch.text = record.securityPatchDate ?: "--"
        binding.txtBootloader.text = record.bootloaderState ?: "--"
        binding.txtApps.text = record.totalAppCount?.toString() ?: "--"
        binding.txtChangedApps.text = record.changedAppCount?.toString() ?: "--"
        binding.txtDelta.text = record.isAppDelta?.toString() ?: "--"
        binding.txtImportantLogs.text = record.importantLogCount.toString()
        binding.txtScanError.text = record.errorMessage ?: "None"
        binding.txtDeviceJson.text = record.deviceReportJson?.let { formatJson(it) } ?: "--"
        binding.txtAppsJson.text = record.appSnapshotJson?.let { formatJson(it) } ?: "--"
        binding.txtLogsJson.text = record.importantLogsJson?.let { formatJson(it) } ?: "--"
    }

    private fun renderMissing() {
        binding.txtTitle.text = "Scan detail"
        binding.txtSubtitle.text = "Record unavailable"
        binding.txtRiskScore.text = "--"
        binding.txtRiskLabel.text = "Waiting"
        binding.txtRiskHeadline.text = "No scan record is available"
        binding.txtRiskReasons.text = "No scan evidence is available yet."
        binding.txtPayloadId.text = "--"
        binding.txtUploadStatus.text = "--"
        binding.txtRetryCount.text = "--"
        binding.txtLastAttempt.text = "--"
        binding.txtUploadedAt.text = "--"
        binding.txtUploadError.text = "None"
        binding.txtStartedAt.text = "--"
        binding.txtCompletedAt.text = "--"
        binding.txtDeviceId.text = "--"
        binding.txtRooted.text = "--"
        binding.txtIntegrity.text = "--"
        binding.txtPatch.text = "--"
        binding.txtBootloader.text = "--"
        binding.txtApps.text = "--"
        binding.txtChangedApps.text = "--"
        binding.txtDelta.text = "--"
        binding.txtImportantLogs.text = "--"
        binding.txtScanError.text = "None"
        binding.txtDeviceJson.text = "--"
        binding.txtAppsJson.text = "--"
        binding.txtLogsJson.text = "--"
    }

    private fun copyPayloadSummary() {
        val record = currentRecord ?: return copyText("Payload summary", "")
        val summary = buildString {
            appendLine("scan_id=${record.id}")
            appendLine("status=${record.status.name}")
            appendLine("trigger=${record.trigger.name}")
            appendLine("payload_id=${record.payloadId ?: "--"}")
            appendLine("upload_status=${record.uploadStatus.name}")
            appendLine("retry_count=${record.retryCount}")
            appendLine("last_upload_attempt=${formatTime(record.lastUploadAttemptAtEpochMs)}")
            appendLine("uploaded_at=${formatTime(record.uploadedAtEpochMs)}")
            appendLine("last_upload_error=${record.lastUploadError ?: "None"}")
        }
        copyText("Payload summary", summary)
    }

    private fun copyAnalystBrief() {
        val record = currentRecord ?: return copyText("Analyst brief", "")
        copyText("Analyst brief", buildAnalystBrief(record))
    }

    private fun shareAnalystBrief() {
        val record = currentRecord
        if (record == null) {
            Toast.makeText(this, "No report available", Toast.LENGTH_SHORT).show()
            return
        }
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "AEGIS Analyst Brief")
            putExtra(Intent.EXTRA_TEXT, buildAnalystBrief(record))
        }
        startActivity(Intent.createChooser(intent, "Share Analyst Brief"))
    }

    private fun buildAnalystBrief(record: ScanRecord): String {
        val brief = RiskBrief.from(record)
        return buildString {
            appendLine("scan_id=${record.id}")
            appendLine("payload_id=${record.payloadId ?: "--"}")
            appendLine("device_id=${record.deviceId ?: "--"}")
            appendLine("status=${record.status.name}")
            appendLine("upload_status=${record.uploadStatus.name}")
            appendLine("retry_count=${record.retryCount}")
            appendLine("important_log_count=${record.importantLogCount}")
            appendLine("total_app_count=${record.totalAppCount ?: "--"}")
            appendLine("changed_app_count=${record.changedAppCount ?: "--"}")
            appendLine("integrity=--")
            appendLine("rooted=${record.isRooted ?: "--"}")
            append(brief.analystText)
        }
    }

    private fun copyText(label: String, value: String) {
        if (value.isBlank()) {
            Toast.makeText(this, "Nothing to copy", Toast.LENGTH_SHORT).show()
            return
        }
        val clipboard = getSystemService(ClipboardManager::class.java)
        clipboard.setPrimaryClip(ClipData.newPlainText(label, value))
        Toast.makeText(this, "$label copied", Toast.LENGTH_SHORT).show()
    }

    private fun formatJson(rawJson: String): String =
        runCatching {
            prettyJson.encodeToString(JsonElement.serializer(), prettyJson.parseToJsonElement(rawJson))
        }.getOrElse { rawJson }

    private fun toggleJson(container: android.view.View, button: android.widget.TextView, label: String) {
        val shouldShow = container.visibility != android.view.View.VISIBLE
        container.visibility = if (shouldShow) android.view.View.VISIBLE else android.view.View.GONE
        button.text = if (shouldShow) "Hide $label" else "Show $label"
    }

    private fun formatTime(epochMs: Long?): String =
        epochMs?.let { dateFormat.format(Date(it)) } ?: "--"

    companion object {
        private const val EXTRA_SCAN_ID = "com.aegis.agent.sample.EXTRA_SCAN_ID"
        private const val MISSING_SCAN_ID = -1L

        fun intent(context: Context, scanId: Long): Intent =
            Intent(context, ScanDetailActivity::class.java)
                .putExtra(EXTRA_SCAN_ID, scanId)
    }
}
