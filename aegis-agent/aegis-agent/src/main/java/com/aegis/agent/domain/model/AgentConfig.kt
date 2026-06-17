package com.aegis.agent.domain.model

import kotlinx.serialization.Serializable

/**
 * AgentConfig — runtime configuration for the AEGIS agent.
 *
 * Passed into [AegisSdk.init] by the host application or MDM provisioning.
 *
 * @param backendUrl       Full URL of the AEGIS ingestion gateway (e.g. https://api.aegis.internal)
 * @param deviceId         Unique device identifier (typically derived from Android ID / enrollment ID)
 * @param enrollmentToken  Short-lived token proving MDM enrollment; exchanged for mTLS cert on first run
 * @param isByodMode       True = personal device; hides personal apps from AppIntelligenceCollector
 * @param scanIntervalMin  How often WorkManager schedules a full device scan (minutes, minimum 15)
 */
@Serializable
data class AgentConfig(
    val backendUrl: String,
    val deviceId: String,
    val enrollmentToken: String,
    val isByodMode: Boolean = false,
    val scanIntervalMin: Long = 60L,
)
