plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.kapt)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.hilt)
}

android {
    namespace = "com.aegis.agent"
    compileSdk = 34

    defaultConfig {
        minSdk = 26

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        consumerProguardFiles("consumer-rules.pro")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs += listOf(
            "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi",
            "-opt-in=kotlinx.serialization.ExperimentalSerializationApi"
        )
    }

    buildFeatures {
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    testOptions {
        targetSdk = 34
        unitTests.all {
            it.useJUnitPlatform() // Required for JUnit5
        }
    }
}

dependencies {
    // Kotlin
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.serialization.json)

    // AndroidX Core
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)

    // WorkManager — reliable background jobs
    implementation(libs.androidx.work.runtime.ktx)

    // DataStore — persistent key-value storage
    implementation(libs.androidx.datastore.preferences)

    // Security Crypto — encrypted config persistence
    implementation(libs.androidx.security.crypto)

    // Room — durable scan result history
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    kapt(libs.androidx.room.compiler)

    // Hilt — dependency injection
    implementation(libs.hilt.android)
    kapt(libs.hilt.compiler)

    // Hilt + WorkManager integration
    implementation(libs.hilt.work)
    kapt(libs.hilt.work.compiler)

    // OkHttp 4.x — HTTP client with certificate pinning
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.okhttp.tls) // Certificate pinning utilities

    // Logging
    implementation(libs.timber)

    // Unit Testing
    testImplementation(libs.junit5.api)
    testImplementation(libs.junit5.params)
    testRuntimeOnly(libs.junit5.engine)
    testImplementation(libs.mockk)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)

    // Android Testing
    androidTestImplementation(libs.mockk.android)
}
