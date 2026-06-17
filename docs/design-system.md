# AEGIS Design System

One dark **cyber-security** visual language shared across three surfaces: the Android scanner app, the AEGIS analyst dashboard, and APK Studio.

---

## Palette

All hex values are defined once and referenced everywhere:

| Token | Hex | Role |
|---|---|---|
| `bg-base` | `#080D13` | Page / root background |
| `bg-surface` | `#111922` | Panel / card background |
| `bg-elevated` | `#182535` | Hover state, active row, input background |
| `bg-score` | `#0A1118` | Score circles, deep-inset elements |
| `bg-sidebar` | `#0D141C` | Navigation sidebar |
| `text-primary` | `#F4F8FB` | Body text |
| `text-secondary` | `#B9C4CF` | Supporting text |
| `text-muted` | `#8FA0B2` | Labels, meta-data |
| `border-subtle` | `#203040` | Default border |
| `border-strong` | `#405468` | Emphasized border |
| `accent` (cyan) | `#64D2FF` | Primary interactive accent |
| `accent-surface` | `#0D2230` | Tinted background for cyan elements |
| `accent-on` | `#071014` | Text *on* cyan fill |
| `violet` | `#A78BFA` | AI / secondary accent |
| `violet-surface` | `#1A1030` | Tinted background for violet elements |

### Risk scale — identical on every surface

| Level | Foreground | Background | Android name |
|---|---|---|---|
| Low | `#46D39A` | `#10241C` | `status_good` / `status_good_surface` |
| Medium | `#F4B740` | `#281F0C` | `status_warn` / `status_warn_surface` |
| High | `#F97316` | `#251508` | `status_high` / `status_high_surface` |
| Critical | `#FF6B6B` | `#2A1114` | `status_danger` / `status_danger_surface` |
| Unknown | `#95A3B3` | `#141A22` | `status_neutral` / `status_neutral_surface` |

Score → label mapping: `score ≥ 80 → Critical`, `≥ 50 → High`, `≥ 25 → Medium`, `< 25 → Low`.

---

## Typography

| Role | Font | Usage |
|---|---|---|
| UI | Inter → system-ui → sans-serif | All prose, labels, nav |
| Mono | JetBrains Mono → Cascadia Code → Consolas | Device IDs, hashes, package names, log messages, timestamps |

Type scale: 11 px caption · 12 px label · 13–14 px body · 18 px panel title · 22 px brand · 30 px page title · 32–36 px score.

---

## Elevation & glow

| Token | Value |
|---|---|
| `shadow-sm` | `0 2px 8px rgba(0,0,0,.45)` |
| `shadow-md` | `0 4px 24px rgba(0,0,0,.55)` |
| `glow-cyan` | `0 0 16px rgba(100,210,255,.12)` |
| `glow-violet` | `0 0 16px rgba(167,139,250,.12)` |

---

## Geometry

| Token | Value |
|---|---|
| `radius-sm` | 6 px |
| `radius-md` | 8 px |
| `radius-lg` | 12 px |
| `radius-pill` | 999 px |

---

## Web implementation

**`frontend/src/tokens.css`** — CSS custom properties; imported at the top of `styles.css`.
Both the AEGIS dashboard and APK Studio import this file for identical tokens.

```css
@import './tokens.css';   /* at top of styles.css */
```

---

## Android implementation

**`values/colors.xml`** — light (day) palette.
**`values-night/colors.xml`** — dark palette (exact match of web tokens above).
**`values/themes.xml`** — uses `Theme.MaterialComponents.DayNight.NoActionBar`, which automatically applies the night resources in dark mode.

Android token names map to web names:

| Android | Web |
|---|---|
| `page_bg` | `bg-base` |
| `surface_primary` | `bg-surface` |
| `surface_secondary` | `bg-sidebar` |
| `surface_score` | `bg-score` |
| `accent` | `accent` |
| `accent_violet` | `violet` |
| `status_good` / `status_good_surface` | `risk-low` / `risk-low-surface` |
| `status_warn` / `status_warn_surface` | `risk-medium` / `risk-medium-surface` |
| `status_high` / `status_high_surface` | `risk-high` / `risk-high-surface` |
| `status_danger` / `status_danger_surface` | `risk-critical` / `risk-critical-surface` |
| `status_neutral` / `status_neutral_surface` | `risk-unknown` / `risk-unknown-surface` |

---

## Components

### RiskBadge / risk chip
- Pill shape (`radius-pill`), 12 px bold all-caps text.
- Background and foreground from the risk scale table above.
- Used in: device rows, timeline items, payload header, Android scan card.

### Panel / card
- Background `bg-surface`, border `border-subtle`, shadow `shadow-sm`, radius `radius-md`, padding 18 px.

### NavButton
- Height 46 px, background transparent at rest, `bg-elevated` on hover/active, `accent` color when active.

### StatusDot / status pill
- Pill, 28 px min-height, 12 px text.
- `.ok` → `risk-low`, `.danger` → `risk-critical`, `.loading` → `accent`.

### Log level badge
- Monospace font, 11 px, uppercase.
- `error`/`assert` → `risk-critical`, `warn` → `risk-medium`, `info` → `accent`, `debug`/`verbose` → muted.

---

## Icon set

- **Web:** `lucide-react` (consistent 19–24 px stroke icons throughout the dashboard).
- **Android:** Material Icons (matching functional categories).
