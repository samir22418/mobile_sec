package com.aegis.agent.data.persistence

import androidx.room.Database
import androidx.room.migration.Migration
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [ScanRecordEntity::class],
    version = 5,
    exportSchema = false,
)
abstract class AegisDatabase : RoomDatabase() {
    abstract fun scanRecordDao(): ScanRecordDao

    companion object {
        val MIGRATION_1_2: Migration = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE scan_records ADD COLUMN integrity_details TEXT")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN integrity_error_code INTEGER")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN integrity_token_hash_sha256 TEXT")
            }
        }

        val MIGRATION_2_3: Migration = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE scan_records ADD COLUMN payload_id TEXT")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN payload_created_at_epoch_ms INTEGER")
            }
        }

        val MIGRATION_3_4: Migration = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE scan_records ADD COLUMN upload_status TEXT NOT NULL DEFAULT 'NOT_READY'")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN last_upload_attempt_at_epoch_ms INTEGER")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN last_upload_error TEXT")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN uploaded_at_epoch_ms INTEGER")
            }
        }

        val MIGRATION_4_5: Migration = object : Migration(4, 5) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE scan_records ADD COLUMN important_log_count INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE scan_records ADD COLUMN important_logs_json TEXT")
            }
        }
    }
}
