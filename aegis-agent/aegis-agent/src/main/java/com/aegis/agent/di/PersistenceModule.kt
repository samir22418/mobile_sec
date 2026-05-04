package com.aegis.agent.di

import android.content.Context
import androidx.room.Room
import com.aegis.agent.data.persistence.AegisDatabase
import com.aegis.agent.data.persistence.ScanRecordDao
import com.aegis.agent.data.persistence.ScanResultRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object PersistenceModule {

    @Provides
    @Singleton
    fun provideAegisDatabase(
        @ApplicationContext context: Context,
    ): AegisDatabase =
        Room.databaseBuilder(
            context,
            AegisDatabase::class.java,
            ScanResultRepository.DATABASE_NAME,
        ).addMigrations(
            AegisDatabase.MIGRATION_1_2,
            AegisDatabase.MIGRATION_2_3,
            AegisDatabase.MIGRATION_3_4,
            AegisDatabase.MIGRATION_4_5,
        )
            .build()

    @Provides
    fun provideScanRecordDao(database: AegisDatabase): ScanRecordDao =
        database.scanRecordDao()
}
