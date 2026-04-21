# Consumer ProGuard rules for AEGIS agent library.
# These rules are included in the app's ProGuard configuration when this library is used.

# Keep AEGIS public API surface
-keep class com.aegis.agent.AegisAgent { *; }
-keep class com.aegis.agent.domain.model.** { *; }
