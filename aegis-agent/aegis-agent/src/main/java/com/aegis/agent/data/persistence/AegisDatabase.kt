package com.aegis.agent.data.persistence

import androidx.room.Database
import androidx.room.migration.Migration
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [ScanRecordEntity::class],
    version = 2,
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
    }
}
