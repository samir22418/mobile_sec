# AEGIS Design System

One dark "cyber security" design system applied consistently across all three
surfaces: the **Android scanner app**, the **analyst dashboard** (React/Vite,
`:5173`), and **APK Studio** (React/Vite, `:8000`).

The shared source of truth lives in [`frontend/src/tokens.css`](../frontend/src/tokens.css).
APK Studio mirrors that file at `apk-studio/frontend/src/tokens.css` and
bridges its own legacy variable names to the canonical tokens via a final
`:root` block appended to its `styles.css`.

---

## Color palette

### Surfaces

| Token | Hex | Use |
|---|---|---|
| `--bg-base` | `#080D13` | Page / root background |
| `--bg-surface` | `#111922` | Panel / card |
| `--bg-elevated` | `#182535` | Hover, active row, input bg |
| `--bg-score` | `#0A1118` | Score circle, deep inset |
| `--bg-sidebar` | `#0D141C` | Navigation sidebar |

### Text

| Token | Hex | Use |
|---|---|---|
| `--text-primary` | `#F4F8FB` | Body text, headings |
| `--text-secondary` | `#B9C4CF` | Supporting labels |
| `--text-muted` | `#8FA0B2` | Timestamps, captions |
| `--text-inverse` | `#071014` | Text on bright accent fill |

### Borders

| Token | Hex |
|---|---|
| `--border-subtle` | `#203040` |
| `--border-strong` | `#405468` |

### Accents

| Token | Hex | Role |
|---|---|---|
| `--accent` | `#64D2FF` | Primary / cyan — interactive elements, charts |
| `--accent-surface` | `#0D2230` | Tinted bg behind cyan elements |
| `--violet` | `#A78BFA` | Secondary / AI — AI pipeline, MITRE, model badges |
| `--violet-surface` | `#1A1030` | Tinted bg behind violet elements |

---

## Risk scale

**Sacred — the same semantic color everywhere: Android gauge, dashboard donut, APK badge.**

| Level | Foreground | Surface | Token pair |
|---|---|---|---|
| Low | `#46D39A` | `#10241C` | `--risk-low` / `--risk-low-surface` |
| Medium | `#F4B740` | `#281F0C` | `--risk-medium` / `--risk-medium-surface` |
| High | `#F97316` | `#251508` | `--risk-high` / `--risk-high-surface` |
| Critical | `#FF6B6B` | `#2A1114` | `--risk-critical` / `--risk-critical-surface` |
| Unknown | `#95A3B3` | `#141A22` | `--risk-unknown` / `--risk-unknown-surface` |

Risk badge component emits `.risk-badge.risk-{level}` on both web apps.

---

## Typography

| Token | Value |
|---|---|
| `--font-ui` | Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI |
| `--font-mono` | JetBrains Mono, Cascadia Code, Fira Code, Consolas |

Monospace is applied to device IDs, package names, hashes, log lines, and
anything that reads as "technical data."

---

## Elevation & glow

| Token | Value |
|---|---|
| `--shadow-sm` | `0 2px 8px rgba(0,0,0,.45)` |
| `--shadow-md` | `0 4px 24px rgba(0,0,0,.55)` |
| `--glow-cyan` | `0 0 16px rgba(100,210,255,.12)` |
| `--glow-violet` | `0 0 16px rgba(167,139,250,.12)` |

---

## Geometry

| Token | Value |
|---|---|
| `--radius-sm` | `6px` |
| `--radius-md` | `8px` |
| `--radius-lg` | `12px` |
| `--radius-pill` | `999px` |
| `--transition` | `120ms ease` |

---

## Data visualizations (Recharts)

Both React apps use **Recharts** for all charts.

| Chart | Surface | Component |
|---|---|---|
| Fleet risk donut | Dashboard Overview | `FleetRiskDonut` (PieChart) — device count by risk level |
| Log volume 7d | Dashboard Overview | `BarChart` — `logs.weekly_counts`, cyan fill |
| Risk score timeline | Dashboard Device detail | `ScoreTimeline` (AreaChart) — cyan gradient area |
| Log level breakdown | Dashboard Logs | `LogLevelChart` (horizontal BarChart) — colored by severity |
| Specialist classifier scores | APK Studio Report | `SpecialistScoreChart` (horizontal BarChart) — severity-colored |
| MITRE technique frequency | APK Studio Report | `MitreTechniqueChart` (horizontal BarChart) — violet fill |

Tooltip style override: `recharts-default-tooltip` in `styles.css` consumes
`--bg-surface` / `--border-subtle` / `--radius-md` for theme consistency.

---

## Brand

- **Favicon:** `frontend/public/aegis-icon.svg` — dark shield with cyan-to-violet
  gradient border and "A" letterform. Wired via `<link rel="icon" type="image/svg+xml">`
  in both apps' `index.html`.
- **Android:** themed launcher icon via `themes.xml` / `colors.xml` in `aegis-agent/`.

---

## Per-surface implementation notes

### Android (`aegis-agent/`)
- `values-night/colors.xml` — token hex values as Android color resources
- `themes.xml` — dark theme consuming those colors
- `RiskBrief.kt` / `ScanDetailActivity.kt` — risk gauge + signal breakdown cards

### Analyst dashboard (`frontend/`)
- `src/tokens.css` — canonical CSS variable definitions
- `src/styles.css` — imports `tokens.css`; all colors via variables
- `src/App.tsx` — `RiskBadge`, `FleetRiskDonut`, `ScoreTimeline`, `LogLevelChart`

### APK Studio (`apk-studio/frontend/`)
- `src/tokens.css` — mirror copy of the canonical tokens
- `src/styles.css` — `@import './tokens.css'` at top; AEGIS Token Bridge `:root`
  block appended at end to override APK Studio's own legacy variable names
- `src/App.jsx` — `SpecialistScoreChart`, `MitreTechniqueChart`
