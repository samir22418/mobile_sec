package com.aegis.agent.sample.ui

import android.content.Intent
import android.content.res.Configuration
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.annotation.ColorRes
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.aegis.agent.AegisSdk
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
import com.aegis.agent.domain.model.UploadStatus
import com.aegis.agent.sample.R
import com.aegis.agent.sample.databinding.ActivityMainBinding
import com.google.android.material.card.MaterialCardView
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import timber.log.Timber
import java.text.DateFormat
import java.util.Date
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : AppCompatActivity() {

    @Inject
    lateinit var scanResultRepository: ScanResultRepository

    private lateinit var binding: ActivityMainBinding
    private val dateFormat: DateFormat by lazy {
        DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT)
    }
    private var latestRecord: ScanRecord? = null
    private var recentRecords: List<ScanRecord> = emptyList()
    private var scanFilter: ScanFilter = ScanFilter.ALL

    override fun onCreate(savedInstanceState: Bundle?) {
        applySavedTheme()
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        Timber.d("AEGIS Agent Sample started")

        binding.btnStartScan.setOnClickListener {
            AegisSdk.requestScanNow(applicationContext)
            Toast.makeText(this, "Security scan queued", Toast.LENGTH_SHORT).show()
        }
        binding.btnToggleTheme.setOnClickListener {
            toggleTheme()
        }
        binding.btnOpenSettings.setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }
        binding.btnOpenDetails.setOnClickListener {
            val recordId = it.tag as? Long
            if (recordId == null) {
                Toast.makeText(this, "No scan detail available", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            startActivity(ScanDetailActivity.intent(this, recordId))
        }
        binding.btnShareLatest.setOnClickListener {
            val record = latestRecord
            if (record == null) {
                Toast.makeText(this, "No report available", Toast.LENGTH_SHORT).show()
            } else {
                shareText("AEGIS Analyst Brief", buildAnalystBrief(record))
            }
        }
        binding.btnFilterAll.setOnClickListener { setFilter(ScanFilter.ALL) }
        binding.btnFilterFailed.setOnClickListener { setFilter(ScanFilter.FAILED) }
        binding.btnFilterUploaded.setOnClickListener { setFilter(ScanFilter.UPLOADED) }
        binding.btnFilterReview.setOnClickListener { setFilter(ScanFilter.REVIEW) }
        updateThemeButton()
        updateFilterButtons()

        lifecycleScope.launch {
            scanResultRepository.observeLatest().collect { record ->
                render(record)
            }
        }
        lifecycleScope.launch {
            scanResultRepository.observeRecent().collect { records ->
                recentRecords = records
                renderRecent()
            }
        }
    }

    private fun render(record: ScanRecord?) {
        if (record == null) {
            renderEmpty()
            return
        }
        latestRecord = record

        binding.txtRecordValue.text = "#${record.id} / ${record.trigger.name.lowercase()}"
        binding.txtPayloadValue.text = record.payloadId ?: "--"
        binding.txtUploadValue.text = record.uploadStatus.name.lowercase()
        binding.txtRetryValue.text = record.retryCount.toString()
        binding.txtLogCountValue.text = record.importantLogCount.toString()
        binding.txtUploadAttemptValue.text = formatTime(record.lastUploadAttemptAtEpochMs)
        binding.txtUploadedAtValue.text = formatTime(record.uploadedAtEpochMs)
        binding.txtUploadErrorValue.text = record.lastUploadError ?: "None"
        binding.txtPatchValue.text = record.securityPatchDate ?: "--"
        binding.txtBootloaderValue.text = record.bootloaderState ?: "--"
        binding.txtAppsValue.text = record.totalAppCount?.toString() ?: "--"
        binding.txtDeltaValue.text = record.changedAppCount?.toString() ?: "--"
        binding.txtLastScan.text = formatTime(record.completedAtEpochMs ?: record.startedAtEpochMs)
        binding.txtErrorValue.text = record.errorMessage ?: "None"
        binding.txtIntegrityDetailsValue.text = "--"
        binding.btnOpenDetails.tag = record.id
        binding.btnOpenDetails.isEnabled = true
        binding.btnShareLatest.isEnabled = true
        renderRiskBrief(RiskBrief.from(record))
        renderChips(record)

        when (record.status) {
            ScanStatus.RUNNING -> renderRunning(record)
            ScanStatus.SUCCESS -> renderSuccess(record)
            ScanStatus.FAILED -> renderFailed(record)
        }
    }

    private fun renderEmpty() {
        binding.progressScan.visibility = View.GONE
        binding.btnStartScan.isEnabled = true
        binding.txtStatus.text = "Ready"
        binding.txtPostureHeadline.text = "No scan saved yet"
        binding.txtLastScan.text = "--"
        binding.txtIntegrityValue.text = "--"
        binding.txtIntegrityDetailsValue.text = "No Play Integrity request has been made yet."
        binding.txtRootValue.text = "--"
        binding.txtAppsValue.text = "--"
        binding.txtDeltaValue.text = "--"
        binding.txtPatchValue.text = "--"
        binding.txtBootloaderValue.text = "--"
        binding.txtRecordValue.text = "--"
        binding.txtPayloadValue.text = "--"
        binding.txtUploadValue.text = "--"
        binding.txtRetryValue.text = "--"
        binding.txtLogCountValue.text = "--"
        binding.txtUploadAttemptValue.text = "--"
        binding.txtUploadedAtValue.text = "--"
        binding.txtUploadErrorValue.text = "None"
        binding.txtErrorValue.text = "None"
        binding.btnOpenDetails.tag = null
        binding.btnOpenDetails.isEnabled = false
        binding.btnShareLatest.isEnabled = false
        binding.txtRiskScore.text = "--"
        binding.txtRiskLabel.text = "Waiting"
        binding.txtRiskHeadline.text = "Run a scan to build a local risk brief"
        binding.txtRiskReasons.text = "No scan evidence is available yet."
        binding.txtRecommendedAction.text = "Recommended Action: Run a scan."
        binding.txtUploadChip.text = "Upload --"
        binding.txtRootChip.text = "Root --"
        binding.txtIntegrityChip.text = "Integrity --"
        GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(color(R.color.surface_score))
            setStroke(4.dp, color(R.color.border_subtle))
        }.also { binding.txtRiskScore.background = it }
        setStatusColors(color(R.color.status_neutral), color(R.color.status_neutral_surface))
    }

    private fun renderRunning(record: ScanRecord) {
        binding.progressScan.visibility = View.VISIBLE
        binding.btnStartScan.isEnabled = false
        binding.txtStatus.text = "Scanning"
        binding.txtPostureHeadline.text = "Collecting device posture and app inventory"
        binding.txtIntegrityValue.text = "--"
        binding.txtRootValue.text = "Pending"
        setStatusColors(color(R.color.accent), color(R.color.accent_surface))
    }

    private fun renderSuccess(record: ScanRecord) {
        binding.progressScan.visibility = View.GONE
        binding.btnStartScan.isEnabled = true
        binding.txtStatus.text = "Complete"
        binding.txtIntegrityValue.text = "--"
        binding.txtRootValue.text = when (record.isRooted) {
            true -> "Detected"
            false -> "Clean"
            null -> "--"
        }

        val danger = color(R.color.status_danger)
        val good = color(R.color.status_good)
        val riskColor = if (record.isRooted == true) danger else good
        val riskSurface = if (record.isRooted == true) {
            color(R.color.status_danger_surface)
        } else {
            color(R.color.status_good_surface)
        }

        binding.txtPostureHeadline.text = if (record.isRooted == true) {
            "Root signals detected"
        } else {
            "Device posture saved"
        }
        setStatusColors(riskColor, riskSurface)
    }

    private fun renderFailed(record: ScanRecord) {
        binding.progressScan.visibility = View.GONE
        binding.btnStartScan.isEnabled = true
        binding.txtStatus.text = "Failed"
        binding.txtPostureHeadline.text = "Scan stopped before completion"
        binding.txtIntegrityValue.text = "--"
        binding.txtRootValue.text = "--"
        setStatusColors(color(R.color.status_danger), color(R.color.status_danger_surface))
    }

    private fun renderRiskBrief(brief: RiskBrief) {
        binding.txtRiskScore.text = brief.score.toString()
        binding.txtRiskLabel.text = brief.label
        binding.txtRiskHeadline.text = brief.headline
        binding.txtRiskReasons.text = brief.reasonText
        binding.txtRecommendedAction.text = "Recommended Action: ${brief.recommendedAction}"
        // Circular gauge: fill with risk-level surface color, stroke with accent color
        val (fillRes, strokeRes) = riskGaugeColors(brief.label)
        GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(color(fillRes))
            setStroke(4.dp, color(strokeRes))
        }.also { binding.txtRiskScore.background = it }
    }

    private fun riskGaugeColors(label: String): Pair<Int, Int> =
        when (label) {
            "Critical", "Blocked" -> R.color.status_danger_surface to R.color.status_danger
            "High"                -> R.color.status_high_surface    to R.color.status_high
            "Watch"               -> R.color.status_warn_surface    to R.color.status_warn
            "Scanning"            -> R.color.accent_surface         to R.color.accent
            else                  -> R.color.status_good_surface    to R.color.status_good
        }

    private fun renderChips(record: ScanRecord) {
        binding.txtUploadChip.text = when (record.uploadStatus) {
            UploadStatus.UPLOADED -> "Uploaded"
            UploadStatus.UPLOADING -> "Uploading"
            UploadStatus.PENDING -> "Queued"
            UploadStatus.FAILED -> "Retrying"
            UploadStatus.NOT_READY -> "Not ready"
        }
        binding.txtUploadChip.setTextColor(colorForUpload(record.uploadStatus))

        binding.txtRootChip.text = when (record.isRooted) {
            true -> "Root detected"
            false -> "Root clean"
            null -> "Root pending"
        }
        binding.txtRootChip.setTextColor(
            when (record.isRooted) {
                true -> color(R.color.status_danger)
                false -> color(R.color.status_good)
                null -> color(R.color.text_muted)
            }
        )

        binding.txtIntegrityChip.text = "Integrity --"
        binding.txtIntegrityChip.setTextColor(color(R.color.text_muted))
    }

    private fun renderRecent() {
        binding.recentScansContainer.removeAllViews()
        val records = filteredRecentRecords()
        if (recentRecords.isEmpty()) {
            binding.txtRecentEmpty.visibility = View.VISIBLE
            binding.txtRecentEmpty.text = "No scan history yet."
            return
        }
        if (records.isEmpty()) {
            binding.txtRecentEmpty.visibility = View.VISIBLE
            binding.txtRecentEmpty.text = "No scans match this filter."
            return
        }

        binding.txtRecentEmpty.visibility = View.GONE
        records.forEach { record ->
            binding.recentScansContainer.addView(recentScanRow(record))
        }
    }

    private fun filteredRecentRecords(): List<ScanRecord> =
        when (scanFilter) {
            ScanFilter.ALL -> recentRecords
            ScanFilter.FAILED -> recentRecords.filter {
                it.status == ScanStatus.FAILED || it.uploadStatus == UploadStatus.FAILED
            }
            ScanFilter.UPLOADED -> recentRecords.filter { it.uploadStatus == UploadStatus.UPLOADED }
            ScanFilter.REVIEW -> recentRecords.filter {
                val brief = RiskBrief.from(it)
                brief.label in setOf("Watch", "High", "Critical", "Blocked")
            }
        }

    private fun setFilter(filter: ScanFilter) {
        scanFilter = filter
        updateFilterButtons()
        renderRecent()
    }

    private fun updateFilterButtons() {
        binding.btnFilterAll.alpha = if (scanFilter == ScanFilter.ALL) 1.0f else 0.58f
        binding.btnFilterFailed.alpha = if (scanFilter == ScanFilter.FAILED) 1.0f else 0.58f
        binding.btnFilterUploaded.alpha = if (scanFilter == ScanFilter.UPLOADED) 1.0f else 0.58f
        binding.btnFilterReview.alpha = if (scanFilter == ScanFilter.REVIEW) 1.0f else 0.58f
    }

    private fun recentScanRow(record: ScanRecord): View {
        val brief = RiskBrief.from(record)
        val card = MaterialCardView(this).apply {
            radius = 8.dp.toFloat()
            strokeWidth = 1.dp
            strokeColor = colorForBrief(brief)
            setCardBackgroundColor(color(R.color.surface_secondary))
            useCompatPadding = false
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            ).apply {
                topMargin = 10.dp
            }
            setOnClickListener {
                startActivity(ScanDetailActivity.intent(this@MainActivity, record.id))
            }
        }

        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(14.dp, 12.dp, 14.dp, 12.dp)
        }

        val title = TextView(this).apply {
            text = "#${record.id}  ${brief.label}  ${uploadLabel(record.uploadStatus)}"
            setTextColor(color(R.color.text_primary))
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        val meta = TextView(this).apply {
            text = "${record.trigger.name.lowercase()} / ${formatTime(record.completedAtEpochMs ?: record.startedAtEpochMs)}"
            setTextColor(color(R.color.text_muted))
            textSize = 12f
        }
        val reasons = TextView(this).apply {
            text = brief.reasons.take(2).joinToString(separator = "  |  ")
            setTextColor(color(R.color.text_secondary))
            textSize = 12f
            maxLines = 2
        }

        body.addView(title)
        body.addView(meta)
        body.addView(reasons)
        card.addView(body)
        return card
    }

    private fun uploadLabel(status: UploadStatus): String =
        when (status) {
            UploadStatus.UPLOADED -> "Uploaded"
            UploadStatus.UPLOADING -> "Uploading"
            UploadStatus.PENDING -> "Queued"
            UploadStatus.FAILED -> "Retrying"
            UploadStatus.NOT_READY -> "Not ready"
        }

    private fun colorForUpload(status: UploadStatus): Int =
        when (status) {
            UploadStatus.UPLOADED -> color(R.color.status_good)
            UploadStatus.UPLOADING,
            UploadStatus.PENDING -> color(R.color.accent)
            UploadStatus.FAILED -> color(R.color.status_warn)
            UploadStatus.NOT_READY -> color(R.color.text_muted)
        }

    private fun colorForBrief(brief: RiskBrief): Int =
        when (brief.label) {
            "Critical", "Blocked" -> color(R.color.status_danger)
            "High"                -> color(R.color.status_high)
            "Watch"               -> color(R.color.status_warn)
            "Scanning"            -> color(R.color.accent)
            else                  -> color(R.color.status_good)
        }

    private fun setStatusColors(accentColor: Int, surfaceColor: Int) {
        binding.statusCard.strokeColor = accentColor
        binding.statusCard.setCardBackgroundColor(surfaceColor)
        binding.txtStatus.setTextColor(accentColor)
    }

    private fun formatTime(epochMs: Long?): String =
        epochMs?.let { dateFormat.format(Date(it)) } ?: "--"

    private fun applySavedTheme() {
        val savedMode = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getInt(KEY_THEME_MODE, AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
        AppCompatDelegate.setDefaultNightMode(savedMode)
    }

    private fun toggleTheme() {
        val newMode = if (isNightMode()) {
            AppCompatDelegate.MODE_NIGHT_NO
        } else {
            AppCompatDelegate.MODE_NIGHT_YES
        }
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .edit()
            .putInt(KEY_THEME_MODE, newMode)
            .apply()
        AppCompatDelegate.setDefaultNightMode(newMode)
    }

    private fun updateThemeButton() {
        binding.btnToggleTheme.text = if (isNightMode()) "Light Mode" else "Dark Mode"
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

    private fun shareText(title: String, value: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, title)
            putExtra(Intent.EXTRA_TEXT, value)
        }
        startActivity(Intent.createChooser(intent, title))
    }

    private fun isNightMode(): Boolean {
        val mask = resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK
        return mask == Configuration.UI_MODE_NIGHT_YES
    }

    private fun color(@ColorRes colorRes: Int): Int =
        ContextCompat.getColor(this, colorRes)

    private val Int.dp: Int
        get() = (this * resources.displayMetrics.density).toInt()

    companion object {
        private const val PREFS_NAME = "aegis_sample_theme"
        private const val KEY_THEME_MODE = "theme_mode"
    }

    private enum class ScanFilter {
        ALL,
        FAILED,
        UPLOADED,
        REVIEW,
    }
}
