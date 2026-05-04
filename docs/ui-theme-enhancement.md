# AEGIS UI Theme Enhancement

## Purpose

This pass improves the scanner UI colors and adds dark/light mode support without changing the agent architecture.

## What Changed

Added theme color resources:

```text
app/src/main/res/values/colors.xml
app/src/main/res/values-night/colors.xml
```

Updated:

```text
app/src/main/res/values/themes.xml
app/src/main/res/layout/activity_main.xml
app/src/main/res/layout/activity_scan_detail.xml
app/src/main/java/com/aegis/agent/sample/ui/MainActivity.kt
```

## UX Improvements

- Light mode and dark mode now use separate palettes.
- Layout colors use semantic resources instead of hardcoded dark hex values.
- Status colors are still meaningful:
  - green for healthy
  - yellow for warning/review
  - red for danger/failure
  - blue for scanning/information
- Recent scan rows now follow the active theme.
- Dashboard has a small `Dark Mode` / `Light Mode` toggle.
- The selected mode is saved locally.

## Verification

Commands:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :aegis-agent:testDebugUnitTest
```

Result:

```text
BUILD SUCCESSFUL
```

