package com.aegis.agent.di

import android.content.Context
import androidx.work.WorkManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.CertificatePinner
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import timber.log.Timber
import java.util.concurrent.TimeUnit
import javax.inject.Singleton
import com.aegis.agent.data.persistence.ConfigRepository

/**
 * NetworkModule — Hilt module that provides a singleton [OkHttpClient].
 *
 * Key features:
 * - Certificate pinning via [CertificatePinner] (pins are loaded from BuildConfig /
 *   a remote config — placeholder pins shown below, replace with real SHA-256 pins)
 * - Logging interceptor suppressed in release builds
 * - Sensible timeouts for mobile networks
 * - Automatically injects the Bearer token if available
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    /**
     * Pins for the AEGIS backend.
     *
     * HOW TO GET REAL PINS:
     *   openssl s_client -connect api.aegis.internal:443 | \
     *     openssl x509 -pubkey -noout | \
     *     openssl pkey -pubin -outform der | \
     *     openssl dgst -sha256 -binary | base64
     *
     * The first pin is the leaf cert; the second is the CA backup pin (required
     * so you can rotate the leaf without locking users out).
     */
    private const val AEGIS_BACKEND_HOST = "api.aegis.internal"
    private const val PIN_LEAF = "sha256/REPLACE_WITH_REAL_LEAF_CERTIFICATE_PIN="
    private const val PIN_BACKUP = "sha256/REPLACE_WITH_REAL_CA_BACKUP_PIN="

    @Provides
    @Singleton
    fun provideOkHttpClient(configRepository: ConfigRepository): OkHttpClient {
        val loggingInterceptor = HttpLoggingInterceptor { message ->
            Timber.tag("OkHttp").d(message)
        }.apply {
            // NEVER log request bodies in production — they contain device telemetry
            level = if (com.aegis.agent.BuildConfig.DEBUG)
                HttpLoggingInterceptor.Level.HEADERS  // no body even in debug
            else
                HttpLoggingInterceptor.Level.NONE
        }

        val authInterceptor = Interceptor { chain ->
            val request = chain.request()
            val token = AgentConfigHolder.getOrLoad(configRepository)?.enrollmentToken
            if (token != null) {
                val newRequest = request.newBuilder()
                    .addHeader("Authorization", "Bearer $token")
                    .build()
                chain.proceed(newRequest)
            } else {
                chain.proceed(request)
            }
        }

        return OkHttpClient.Builder()
            .applyCertificatePinningIfConfigured()
            .addInterceptor(authInterceptor)
            .addInterceptor(loggingInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS) // APK metadata uploads can be large
            .retryOnConnectionFailure(true)
            .build()
    }

    private fun OkHttpClient.Builder.applyCertificatePinningIfConfigured(): OkHttpClient.Builder {
        val configuredPins = listOf(PIN_LEAF, PIN_BACKUP)
            .filterNot { it.contains("REPLACE_WITH_REAL") }

        if (configuredPins.isEmpty()) {
            Timber.w("NetworkModule: certificate pinning disabled until real pins are configured")
            return this
        }

        val certificatePinner = CertificatePinner.Builder().apply {
            configuredPins.forEach { pin -> add(AEGIS_BACKEND_HOST, pin) }
        }.build()

        return certificatePinner(certificatePinner)
    }

    @Provides
    @Singleton
    fun provideWorkManager(@ApplicationContext context: Context): WorkManager =
        WorkManager.getInstance(context)
}
