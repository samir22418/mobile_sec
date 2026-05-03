import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.kapt)
    alias(libs.plugins.hilt)
}

val localProperties = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) {
        file.inputStream().use { load(it) }
    }
}

val aegisCloudProjectNumber = (
    localProperties.getProperty("AEGIS_CLOUD_PROJECT_NUMBER")
        ?: providers.gradleProperty("AEGIS_CLOUD_PROJECT_NUMBER").orNull
        ?: "0"
).trim().toLongOrNull() ?: 0L

android {
    namespace = "com.aegis.agent.sample"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.aegis.agent.sample"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        buildConfigField("long", "AEGIS_CLOUD_PROJECT_NUMBER", "${aegisCloudProjectNumber}L")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

}

dependencies {
    // AEGIS Agent Library
    implementation(project(":aegis-agent"))

    // AndroidX
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // WorkManager
    implementation(libs.androidx.work.runtime.ktx)

    // Hilt
    implementation(libs.hilt.android)
    kapt(libs.hilt.compiler)
    implementation(libs.hilt.work)
    kapt(libs.hilt.work.compiler)

    // Logging
    implementation(libs.timber)
}
