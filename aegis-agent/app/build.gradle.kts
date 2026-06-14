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

val aegisBackendUrl = (
    localProperties.getProperty("AEGIS_BACKEND_URL")
        ?: providers.gradleProperty("AEGIS_BACKEND_URL").orNull
        ?: "https://api.aegis.internal"
).trim()

val aegisEnrollmentToken = (
    localProperties.getProperty("AEGIS_ENROLLMENT_TOKEN")
        ?: providers.gradleProperty("AEGIS_ENROLLMENT_TOKEN").orNull
        ?: "sample-token"
).trim()

fun String.asBuildConfigString(): String =
    "\"" + replace("\\", "\\\\").replace("\"", "\\\"") + "\""

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
        buildConfigField("String", "AEGIS_BACKEND_URL", aegisBackendUrl.asBuildConfigString())
        buildConfigField("String", "AEGIS_ENROLLMENT_TOKEN", aegisEnrollmentToken.asBuildConfigString())
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
    implementation(libs.kotlinx.serialization.json)
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
