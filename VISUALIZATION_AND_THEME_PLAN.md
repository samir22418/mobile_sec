# AEGIS — Unified Theme & Visualization Plan

**Goal:** One professional **dark "cyber security"** design system applied consistently across all three surfaces — the **Android scanner app**, the **AEGIS analyst dashboard**, and **APK Studio** — plus upgraded **data visualizations** end to end.
**Order:** Android first, then the dashboard, then APK Studio (per your preference), finishing with cross-system consistency.

---

## Guiding principles
- **One source of truth.** Define the design system once (tokens), then implement it per platform. No per-screen ad-hoc styling.
- **Security-product look.** Dark surfaces, restrained neon accents (cyan/violet), monospace for technical data (device IDs, hashes, packages), generous spacing, subtle glow/elevation.
- **Risk semantics are sacred.** The same risk colors mean the same thing everywhere: **Low = green, Medium = amber, High = orange, Critical = red, Unknown = grey.** Identical on the Android gauge, the dashboard donut, and the APK report.
- **Every view has loading / empty / error states.** No blank screens in a demo.

---

## Phase 0 — Define the design system (do once, first)
The shared spec that everything else implements.

- [ ] **Color tokens:** background layers (base / surface / elevated), text (primary / muted / inverse), border, accent (cyan primary, violet secondary), and the 5-step **risk scale**. Define hex values once.
- [ ] **Typography:** UI sans (e.g., Inter / system), **monospace** (e.g., JetBrains Mono) for IDs, hashes, package names, logs. Type scale (display / title / body / caption).
- [ ] **Spacing, radius, elevation/glow, iconography** (one icon set — `lucide` on web; matching Material icons on Android).
- [ ] **Component specs:** panel/card, nav, buttons, **risk chip/badge**, tables, chart styling, status dot, empty/loading/error.
- [ ] **Deliverables:**
  - `docs/design-system.md` (the spec + palette).
  - Web: a shared **`tokens.css`** (CSS variables) imported by *both* the dashboard and APK Studio.
  - Android: `colors.xml` + `themes.xml` (+ a small style set) mapping the same tokens.

---

## Phase 1 — Android scanner app (first)
*Stack: View/XML-based UI (`themes.xml`, `colors.xml`, `activity_main.xml`, `MainActivity.kt`, `RiskBrief.kt`, `ScanDetailActivity.kt`, `SettingsActivity.kt`).*

- [ ] **Apply the dark theme** via `themes.xml`/`colors.xml` (single dark theme using the Phase-0 palette; retire the ad-hoc dark/light split or rebuild light as a proper token variant).
- [ ] **Risk visualization:** replace the plain score with a **circular risk gauge** (custom view or `MPAndroidChart`) colored by the risk scale, with the verdict label inside.
- [ ] **Signal breakdown cards:** root, integrity, security-patch age, sideloaded/suspicious apps, important logs — each a card with a **severity chip** and a one-line reason, scannable at a glance.
- [ ] **Scan flow polish:** progress state, "Connect Device" settings screen, empty/error states all themed; monospace for device ID/token fields.
- [ ] **Result:** the agent screens look like one cohesive, professional security app.

## Phase 2 — AEGIS analyst dashboard (React / Vite / TS)
*Stack: `frontend/src/App.tsx`, `styles.css`, `lucide-react`.*

- [ ] **Refactor `styles.css`** to consume the shared `tokens.css` (CSS variables) — remove hardcoded colors.
- [ ] **Adopt one chart library** (recommend **Recharts**) for all dashboard charts.
- [ ] **Overview tab:** fleet **risk-distribution donut** (by label), device/payload counts, **recent high-risk devices** list, system-status row (DB / Ollama / APK Studio).
- [ ] **Device detail:** **risk gauge**, **risk-over-time timeline chart**, reasons/evidence panel with severity coloring.
- [ ] **Logs tab:** cluster view + **level/rule breakdown chart**, redacted-log table with severity colors and monospace.
- [ ] **AI tab:** visualize the pipeline — deterministic vs final score, **evidence lineage**, model-run cards.
- [ ] **Chat tab:** show the **in-context device card** (which device the chat is grounded on), polished message bubbles, model/route/safety badges. *(Ties into the chatbot polish from the assessment.)*

## Phase 3 — APK Studio frontend (React / Vite)
*Already "dark cyber" — the job is to align it to the **same tokens** so the two web apps are visually identical, not just both dark.*

- [ ] **Reconcile palette/typography/components** with the shared `tokens.css` so navigating between the dashboard's "APK Analyzer" tab and APK Studio feels seamless.
- [ ] **Visualizations:** static/dynamic findings, **MITRE ATT&CK matrix/heatmap**, **specialist-classifier scores** (radar or grouped bars), risk gauge, and the **evaluation dashboard** (confusion matrix, precision/recall/F1).
- [ ] **Report styling** aligned to the design system (HTML/PDF).

## Phase 4 — Cross-system consistency & polish
- [ ] **Shared web components:** extract a small set (RiskBadge, Gauge, StatCard, Panel, StatusDot) used by *both* React apps.
- [ ] **Consistent risk colors** verified on Android gauge, dashboard donut, and APK report (same hexes).
- [ ] Unified **loading/empty/error** components; accessibility (dark-theme contrast, focus states).
- [ ] **Brand consistency:** one logo/wordmark + favicon across web apps and the Android launcher/app bar.

## Phase 5 — Verify & demo
- [ ] Build and run all three; screenshot each surface; confirm one cohesive look end to end.
- [ ] Update `docs/design-system.md` with final palette + screenshots; add a short "AEGIS visual identity" section to the README.

---

## Suggested sequence & effort
| Phase | Surface | Effort |
|------|---------|--------|
| 0 | Design tokens (shared) | ~0.5 day |
| 1 | Android app theme + gauge + signal cards | ~1.5–2 days |
| 2 | Dashboard theme + charts (overview/device/logs/AI/chat) | ~2–3 days |
| 3 | APK Studio align tokens + MITRE/classifier/eval viz | ~2 days |
| 4 | Shared components, color/brand consistency, a11y | ~1 day |
| 5 | Build, screenshot, document | ~0.5 day |

---

## Notes
- **Where I help vs Claude Code:** I'm well-suited to author the **design-system spec, token files, and screenshots/verification**, and to drive the live UI checks. The bulk **Kotlin (Android views/gauge) and React/TS (charts, components)** editing across three apps is large multi-file coding — that moves fastest in **Claude Code**, with me defining the tokens and verifying the result visually.
- **Chatbot tie-in (optional, from the assessment):** while restyling the chat tab, also (a) always surface the in-context device, (b) let users pick a device inside chat, and (c) optionally support "ask about device X" lookups — these close the grounding caveats.
- **Decision already made:** dark cyber-security aesthetic + full charts/visualization scope.
