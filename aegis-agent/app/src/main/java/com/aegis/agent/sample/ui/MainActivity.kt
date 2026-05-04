package com.aegis.agent.sample.ui

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.aegis.agent.AegisSdk
import com.aegis.agent.data.persistence.ScanResultRepository
import com.aegis.agent.domain.model.IntegrityVerdict
import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        Timber.d("AEGIS Agent Sample started")

        binding.btnStartScan.setOnClickListener {
            AegisSdk.requestScanNow(applicationContext)
            Toast.makeText(this, "Security scan queued", Toast.LENGTH_SHORT).show()
        }
        binding.btnOpenDetails.setOnClickListener {
            val recordId = it.tag as? Long
            if (recordId == null) {
                Toast.makeText(this, "No scan detail available", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            startActivity(ScanDetailActivity.intent(this, recordId))
        }

        lifecycleScope.launch {
            scanResultRepository.observeLatest().collect { record ->
                render(record)
            }
        }
        lifecycleScope.launch {
            scanResultRepository.observeRecent().collect { records ->
                renderRecent(records)
            }
        }
    }

    private fun render(record: ScanRecord?) {
        if (record == null) {
            renderEmpty()
            return
        }

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
        binding.txtIntegrityDetailsValue.text = integrityDetails(record)
        binding.btnOpenDetails.tag = record.id
        binding.btnOpenDetails.isEnabled = true
        renderRiskBrief(RiskBrief.from(record))

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
        binding.txtRiskScore.text = "--"
        binding.txtRiskLabel.text = "Waiting"
        binding.txtRiskHeadline.text = "Run a scan to build a local risk brief"
        binding.txtRiskReasons.text = "No scan evidence is available yet."
        setStatusColors(COLOR_NEUTRAL, COLOR_NEUTRAL_SURFACE)
    }

    private fun renderRunning(record: ScanRecord) {
        binding.progressScan.visibility = View.VISIBLE
        binding.btnStartScan.isEnabled = false
        binding.txtStatus.text = "Scanning"
        binding.txtPostureHeadline.text = "Collecting device posture and app inventory"
        binding.txtIntegrityValue.text = record.integrityVerdict?.let { displayIntegrity(it) } ?: "Pending"
        binding.txtRootValue.text = "Pending"
        setStatusColors(COLOR_ACCENT, COLOR_ACCENT_SURFACE)
    }

    private fun renderSuccess(record: ScanRecord) {
        binding.progressScan.visibility = View.GONE
        binding.btnStartScan.isEnabled = true
        binding.txtStatus.text = "Complete"
        binding.txtIntegrityValue.text = record.integrityVerdict?.let { displayIntegrity(it) } ?: "--"
        binding.txtRootValue.text = when (record.isRooted) {
            true -> "Detected"
            false -> "Clean"
            null -> "--"
        }

        val riskColor = when {
            record.isRooted == true -> COLOR_DANGER
            record.integrityVerdict == IntegrityVerdict.FAILS -> COLOR_DANGER
            record.integrityVerdict == IntegrityVerdict.REQUIRES_BACKEND_VERIFICATION -> COLOR_WARN
            record.integrityVerdict == IntegrityVerdict.NOT_CONFIGURED -> COLOR_WARN
            record.integrityVerdict == IntegrityVerdict.UNAVAILABLE -> COLOR_WARN
            record.integrityVerdict == IntegrityVerdict.API_ERROR -> COLOR_WARN
            record.integrityVerdict == IntegrityVerdict.MEETS_BASIC_INTEGRITY -> COLOR_WARN
            else -> COLOR_GOOD
        }
        val riskSurface = when (riskColor) {
            COLOR_DANGER -> COLOR_DANGER_SURFACE
            COLOR_WARN -> COLOR_WARN_SURFACE
            else -> COLOR_GOOD_SURFACE
        }

        binding.txtPostureHeadline.text = when {
            record.isRooted == true -> "Root signals detected"
            record.integrityVerdict == IntegrityVerdict.FAILS -> "Integrity check failed"
            record.integrityVerdict == IntegrityVerdict.REQUIRES_BACKEND_VERIFICATION -> "Integrity token saved"
            record.integrityVerdict == IntegrityVerdict.NOT_CONFIGURED -> "Integrity setup needed"
            record.integrityVerdict == IntegrityVerdict.UNAVAILABLE -> "Integrity unavailable"
            record.integrityVerdict == IntegrityVerdict.API_ERROR -> "Integrity retry needed"
            else -> "Device posture saved"
        }
        setStatusColors(riskColor, riskSurface)
    }

    private fun renderFailed(record: ScanRecord) {
        binding.progressScan.visibility = View.GONE
        binding.btnStartScan.isEnabled = true
        binding.txtStatus.text = "Failed"
        binding.txtPostureHeadline.text = "Scan stopped before completion"
        binding.txtIntegrityValue.text = record.integrityVerdict?.let { displayIntegrity(it) } ?: "--"
        binding.txtRootValue.text = "--"
        setStatusColors(COLOR_DANGER, COLOR_DANGER_SURFACE)
    }

    private fun renderRiskBrief(brief: RiskBrief) {
        binding.txtRiskScore.text = brief.score.toString()
        binding.txtRiskLabel.text = brief.label
        binding.txtRiskHeadline.text = brief.headline
        binding.txtRiskReasons.text = brief.reasonText
    }

    private fun renderRecent(records: List<ScanRecord>) {
        binding.recentScansContainer.removeAllViews()
        if (records.isEmpty()) {
            binding.txtRecentEmpty.visibility = View.VISIBLE
            return
        }

        binding.txtRecentEmpty.visibility = View.GONE
        records.forEach { record ->
            binding.recentScansContainer.addView(recentScanRow(record))
        }
    }

    private fun recentScanRow(record: ScanRecord): View {
        val brief = RiskBrief.from(record)
        val card = MaterialCardView(this).apply {
            radius = 8.dp.toFloat()
            strokeWidth = 1.dp
            strokeColor = colorForBrief(brief)
            setCardBackgroundColor(Color.parseColor("#0D141C"))
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
            text = "#${record.id}  ${brief.label}  ${record.uploadStatus.name.lowercase()}"
            setTextColor(Color.parseColor("#F4F8FB"))
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        val meta = TextView(this).apply {
            text = "${record.trigger.name.lowercase()} / ${formatTime(record.completedAtEpochMs ?: record.startedAtEpochMs)}"
            setTextColor(Color.parseColor("#95A3B3"))
            textSize = 12f
        }
        val reasons = TextView(this).apply {
            text = brief.reasons.take(2).joinToString(separator = "  |  ")
            setTextColor(Color.parseColor("#B9C4CF"))
            textSize = 12f
            maxLines = 2
        }

        body.addView(title)
        body.addView(meta)
        body.addView(reasons)
        card.addView(body)
        return card
    }

    private fun colorForBrief(brief: RiskBrief): Int =
        when (brief.label) {
            "Critical" -> COLOR_DANGER
            "High" -> COLOR_WARN
            "Watch" -> COLOR_ACCENT
            "Scanning" -> COLOR_ACCENT
            "Blocked" -> COLOR_DANGER
            else -> COLOR_GOOD
        }

    private fun displayIntegrity(verdict: IntegrityVerdict): String =
        when (verdict) {
            IntegrityVerdict.MEETS_STRONG_INTEGRITY -> "Strong"
            IntegrityVerdict.MEETS_DEVICE_INTEGRITY -> "Device"
            IntegrityVerdict.MEETS_BASIC_INTEGRITY -> "Basic"
            IntegrityVerdict.FAILS -> "Failed"
            IntegrityVerdict.REQUIRES_BACKEND_VERIFICATION -> "Token saved"
            IntegrityVerdict.NOT_CONFIGURED -> "Not configured"
            IntegrityVerdict.UNAVAILABLE -> "Unavailable"
            IntegrityVerdict.API_ERROR -> "API error"
        }

    private fun integrityDetails(record: ScanRecord): String {
        val details = record.integrityDetails ?: return "No Integrity detail saved."
        val errorCode = record.integrityErrorCode?.let { " Error code: $it." }.orEmpty()
        val tokenHash = record.integrityTokenHashSha256?.take(12)?.let { " Token hash: $it..." }.orEmpty()
        return details + errorCode + tokenHash
    }

    private fun setStatusColors(accentColor: Int, surfaceColor: Int) {
        binding.statusCard.strokeColor = accentColor
        binding.statusCard.setCardBackgroundColor(surfaceColor)
        binding.txtStatus.setTextColor(accentColor)
    }

    private fun formatTime(epochMs: Long?): String =
        epochMs?.let { dateFormat.format(Date(it)) } ?: "--"

    private val Int.dp: Int
        get() = (this * resources.displayMetrics.density).toInt()

    companion object {
        private val COLOR_GOOD = Color.parseColor("#46D39A")
        private val COLOR_GOOD_SURFACE = Color.parseColor("#10241C")
        private val COLOR_WARN = Color.parseColor("#F4B740")
        private val COLOR_WARN_SURFACE = Color.parseColor("#281F0C")
        private val COLOR_DANGER = Color.parseColor("#FF6B6B")
        private val COLOR_DANGER_SURFACE = Color.parseColor("#2A1114")
        private val COLOR_ACCENT = Color.parseColor("#64D2FF")
        private val COLOR_ACCENT_SURFACE = Color.parseColor("#0D2230")
        private val COLOR_NEUTRAL = Color.parseColor("#95A3B3")
        private val COLOR_NEUTRAL_SURFACE = Color.parseColor("#141A22")
    }
}
