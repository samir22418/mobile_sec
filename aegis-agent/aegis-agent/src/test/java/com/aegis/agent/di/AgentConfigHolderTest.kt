package com.aegis.agent.di

import com.aegis.agent.data.persistence.ConfigRepository
import com.aegis.agent.domain.model.AgentConfig
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertSame
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("AgentConfigHolder")
class AgentConfigHolderTest {

    private val repository: ConfigRepository = mockk()

    @AfterEach
    fun tearDown() {
        AgentConfigHolder.config = null
    }

    @Test
    @DisplayName("getOrLoad returns in-memory config without reading persistence")
    fun `getOrLoad prefers memory config`() {
        val memoryConfig = config(deviceId = "memory-device")
        AgentConfigHolder.config = memoryConfig

        val result = AgentConfigHolder.getOrLoad(repository)

        assertSame(memoryConfig, result)
        verify(exactly = 0) { repository.load() }
    }

    @Test
    @DisplayName("getOrLoad restores persisted config when memory is empty")
    fun `getOrLoad restores persisted config`() {
        val storedConfig = config(deviceId = "stored-device")
        every { repository.load() } returns storedConfig

        val result = AgentConfigHolder.getOrLoad(repository)

        assertEquals(storedConfig, result)
        assertEquals(storedConfig, AgentConfigHolder.config)
        verify(exactly = 1) { repository.load() }
    }

    private fun config(deviceId: String): AgentConfig =
        AgentConfig(
            backendUrl = "https://api.aegis.test",
            deviceId = deviceId,
            enrollmentToken = "token",
            isByodMode = false,
            scanIntervalMin = 60L,
        )
}
