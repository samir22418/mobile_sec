# aegis-agent

> **AEGIS** — Android Enterprise Guard & Intelligence Security  
> **Module:** Core EDR Agent Library (Phase 1)

---

## Module Structure

```
aegis-agent/
├── build.gradle.kts             # Root project build file
├── settings.gradle.kts          # Module inclusion & repo config
├── gradle/
│   └── libs.versions.toml       # Version catalog (single source of truth)
│
└── aegis-agent/                 # Library module
    ├── build.gradle.kts         # Module dependencies & build config
    ├── src/
    │   └── main/
    │       ├── AndroidManifest.xml
    │       └── java/com/aegis/agent/
    │           ├── AegisApplication.kt          # @HiltAndroidApp entry point
    │           ├── AegisSdk.kt                  # Public SDK API
    │           │
    │           ├── di/
    │           │   └── NetworkModule.kt         # Hilt: OkHttpClient with cert pinning
    │           │
    │           ├── data/
    │           │   ├── scanner/                 # [Prompt 1.2] DeviceScanner
    │           │   ├── apps/                    # [Prompt 1.3] AppIntelligenceCollector
    │           │   └── worker/
    │           │       └── TelemetrySyncWorker.kt
    │           │
    │           └── domain/
    │               ├── model/
    │               │   └── AgentConfig.kt       # SDK configuration contract
    │               └── usecase/                 # [Prompts 1.2, 1.3]
```

---

## Clean Architecture Layers

| Layer            | Package                       | Responsibility                                      |
|------------------|-------------------------------|-----------------------------------------------------|
| **Data**         | `agent/data/`                 | Android APIs, device sensors, network, persistence  |
| **Domain**       | `agent/domain/`               | Business logic, use cases, pure Kotlin models       |
| **Presentation** | `agent/presentation/`         | Workers, ViewModels, UI (none in library module)    |

**Rule:** Dependencies only flow inward — `data → domain`, never `domain → data`.

---

## Technology Decisions

| Technology               | Why                                                                 |
|--------------------------|---------------------------------------------------------------------|
| **Hilt**                 | Compile-time verified DI; zero runtime reflection overhead          |
| **WorkManager**          | Survives process death + battery optimization; guaranteed execution |
| **Kotlin Coroutines**    | Structured concurrency; all blocking APIs wrapped in `suspend`      |
| **kotlinx.serialization**| Reflection-free JSON; safe for obfuscated (R8) builds              |
| **OkHttp 4.x**           | Certificate pinning via `CertificatePinner`; battle-tested on Android |
| **Timber**               | Zero-overhead logging in release; pluggable crash reporters         |

---

## Getting Started

### 1. Build the module

```bash
./gradlew :aegis-agent:assembleDebug
```

### 2. Verify Hilt is set up correctly

```bash
./gradlew :aegis-agent:kaptDebugKotlin
# Should complete with no @HiltAndroidApp or @Inject errors
```

### 3. Embed in a host app

```kotlin
// In your Application class:
AegisSdk.init(
    context = this,
    config = AgentConfig(
        backendUrl = "https://api.aegis.internal",
        deviceId = getDeviceId(),
        enrollmentToken = mdmToken,
        isByodMode = false,
        scanIntervalMin = 60L
    )
)
```

---

## ✅ Prompt 1.1 Checklist

- [x] `build.gradle.kts` — all dependencies declared via version catalog
- [x] `settings.gradle.kts` — module included correctly
- [x] `libs.versions.toml` — single source of truth for all versions
- [x] `AndroidManifest.xml` — INTERNET, QUERY_ALL_PACKAGES, FOREGROUND_SERVICE declared
- [x] `AegisApplication.kt` — `@HiltAndroidApp` + `Configuration.Provider` for WorkManager
- [x] `NetworkModule.kt` — OkHttpClient with `CertificatePinner` + logging
- [x] `AegisSdk.kt` — public entry point; WorkManager scheduling
- [x] `TelemetrySyncWorker.kt` — `@HiltWorker` scaffold for Prompts 1.2 / 1.3
- [x] Folder structure: `data/` · `domain/` · `presentation/`

---

## Next Steps (Prompt 1.2)

Implement `DeviceScanner` in `agent/data/scanner/`:
- Root detection (su binary, Build.TAGS, Superuser.apk)
- Play Integrity API query
- Security patch date
- Bootloader state
