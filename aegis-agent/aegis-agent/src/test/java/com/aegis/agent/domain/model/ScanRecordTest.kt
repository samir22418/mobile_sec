package com.aegis.agent.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test

@DisplayName("ScanRecord upload status")
class ScanRecordTest {

    @Test
    @DisplayName("UploadStatus.fromValue maps known values")
    fun `fromValue maps known upload status values`() {
        assertEquals(UploadStatus.NOT_READY, UploadStatus.fromValue("NOT_READY"))
        assertEquals(UploadStatus.PENDING, UploadStatus.fromValue("PENDING"))
        assertEquals(UploadStatus.UPLOADING, UploadStatus.fromValue("UPLOADING"))
        assertEquals(UploadStatus.UPLOADED, UploadStatus.fromValue("UPLOADED"))
        assertEquals(UploadStatus.FAILED, UploadStatus.fromValue("FAILED"))
    }

    @Test
    @DisplayName("UploadStatus.fromValue defaults unknown values to NOT_READY")
    fun `fromValue defaults unknown upload status values`() {
        assertEquals(UploadStatus.NOT_READY, UploadStatus.fromValue(null))
        assertEquals(UploadStatus.NOT_READY, UploadStatus.fromValue(""))
        assertEquals(UploadStatus.NOT_READY, UploadStatus.fromValue("SOMETHING_ELSE"))
    }
}
