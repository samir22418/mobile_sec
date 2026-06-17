package com.aegis.agent.sample.ui

import com.aegis.agent.domain.model.ScanRecord
import com.aegis.agent.domain.model.ScanStatus
import com.aegis.agent.domain.model.UploadStatus
import java.util.concurrent.TimeUnit

data class RiskBrief(
    val score: Int,
    val label: String,
    val headline: String,
    val recommendedAction: String,
    val reasons: List<String>,
) {
    val reasonText: String
        get() = reasons.joinToString(separator = "\n") { "- $it" }

    val analystText: String
        get() = buildString {
            appendLine("risk_score=$score")
            appendLine("risk_label=$label")
            appendLine("headline=$headline")
            appendLine("recommended_action=$recommendedAction")
            appendLine("reasons=")
            append(reasonText.ifBlank { "- No notable local risk signals." })
        }

    companion object {
        fun from(record: ScanRecord): RiskBrief {
            if (record.status == ScanStatus.RUNNING) {
                return RiskBrief(
                    score = 0,
                    label = "Scanning",
                    headline = "Scan in progress",
                    recommendedAction = "Wait for this scan to finish.",
                    reasons = listOf("Device posture and app inventory are still being collected."),
                )
            }

            if (record.status == ScanStatus.FAILED) {
                return RiskBrief(
                    score = 100,
                    label = "Blocked",
                    headline = "Scan failed before completion",
                    recommendedAction = "Check the scan error and run the scan again.",
                    reasons = listOf(record.errorMessage ?: "The worker returned a failed scan state."),
                )
            }

            val reasons = mutableListOf<String>()
            var score = 10

            if (record.isRooted == true) {
                score += 35
                reasons += "Root indicators were detected."
            }

            val changedApps = record.changedAppCount ?: 0
            if (changedApps >= 25) {
                score += 12
                reasons += "Large app inventory change detected: $changedApps apps."
            } else if (changedApps > 0 && record.isAppDelta == true) {
                score += 5
                reasons += "App inventory delta contains $changedApps changed apps."
            }

            if (record.importantLogCount >= 10) {
                score += 12
                reasons += "Important log volume is elevated: ${record.importantLogCount} entries."
            } else if (record.importantLogCount > 0) {
                score += 5
                reasons += "Important logs were captured: ${record.importantLogCount} entries."
            }

            if (record.uploadStatus == UploadStatus.FAILED) {
                score += 8
                reasons += "Latest upload failed and remains queued for retry."
            }

            if (record.retryCount > 0) {
                score += minOf(10, record.retryCount * 3)
                reasons += "Upload retry count is ${record.retryCount}."
            }

            val patchAgeDays = patchAgeDays(record.securityPatchDate)
            if (patchAgeDays != null && patchAgeDays > 90) {
                score += 10
                reasons += "Security patch appears older than 90 days."
            }

            val boundedScore = score.coerceIn(0, 100)
            val label = when {
                boundedScore >= 75 -> "Critical"
                boundedScore >= 50 -> "High"
                boundedScore >= 25 -> "Watch"
                else -> "Low"
            }
            val headline = when (label) {
                "Critical" -> "Immediate review recommended"
                "High"     -> "Backend verification recommended"
                "Watch"    -> "Review notable signals"
                else       -> "No major local signals"
            }
            val recommendedAction = when {
                record.uploadStatus == UploadStatus.FAILED -> "Check failed upload error and wait for retry."
                record.uploadStatus == UploadStatus.PENDING -> "Wait for automatic upload retry."
                record.isRooted == true -> "Review root indicators before trusting this device."
                boundedScore >= 50 -> "Review the analyst brief and raw evidence."
                else -> "No action needed for the local POC view."
            }

            return RiskBrief(
                score = boundedScore,
                label = label,
                headline = headline,
                recommendedAction = recommendedAction,
                reasons = reasons.ifEmpty { listOf("No notable local risk signals.") },
            )
        }

        private fun patchAgeDays(value: String?): Long? {
            if (value.isNullOrBlank()) return null
            val parts = value.split("-")
            if (parts.size != 3) return null
            val year  = parts[0].toIntOrNull() ?: return null
            val month = parts[1].toIntOrNull() ?: return null
            val day   = parts[2].toIntOrNull() ?: return null
            val calendar = java.util.Calendar.getInstance().apply {
                set(year, month - 1, day, 0, 0, 0)
                set(java.util.Calendar.MILLISECOND, 0)
            }
            val diff = System.currentTimeMillis() - calendar.timeInMillis
            return TimeUnit.MILLISECONDS.toDays(diff).takeIf { it >= 0 }
        }
    }
}
