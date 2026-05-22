from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "generated" / "backend-next-steps-roadmap"
PDF_PATH = ROOT / "docs" / "backend-next-steps-roadmap.pdf"

W = 2400
H = 1600

BG = "#f7f9fc"
INK = "#182033"
MUTED = "#5f6f89"
LINE = "#7b8799"
WHITE = "#ffffff"
BLUE = "#dbeafe"
BLUE_D = "#2563eb"
GREEN = "#dcfce7"
GREEN_D = "#16a34a"
YELLOW = "#fef3c7"
YELLOW_D = "#d97706"
RED = "#fee2e2"
RED_D = "#dc2626"
PURPLE = "#ede9fe"
PURPLE_D = "#7c3aed"
CYAN = "#cffafe"
CYAN_D = "#0891b2"
GRAY = "#e5e7eb"
GRAY_D = "#4b5563"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


TITLE = font(54, True)
SUBTITLE = font(27)
H1 = font(38, True)
H2 = font(29, True)
BODY = font(25)
SMALL = font(22)
TINY = font(19)


def wrapped(text: str, chars: int) -> list[str]:
    lines: list[str] = []
    for line in text.split("\n"):
        lines.extend(wrap(line, width=chars) or [""])
    return lines


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((80, 54), title, fill=INK, font=TITLE)
    draw.text((82, 126), subtitle, fill=MUTED, font=SUBTITLE)
    draw.line((80, 176, W - 80, 176), fill="#d9e1ec", width=3)
    return img, draw


def card(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    size: tuple[int, int],
    title: str,
    body: str,
    fill: str,
    accent: str,
    chars: int = 36,
) -> None:
    x, y = xy
    w, h = size
    draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=WHITE, outline="#d8e0eb", width=3)
    draw.rounded_rectangle((x, y, x + w, y + 16), radius=18, fill=accent)
    draw.rectangle((x, y + 8, x + w, y + 16), fill=accent)
    draw.rounded_rectangle((x + 24, y + 34, x + 76, y + 86), radius=14, fill=fill, outline=accent, width=2)
    draw.text((x + 95, y + 34), title, fill=INK, font=H2)
    body_lines = wrapped(body, chars)
    ty = y + 104
    line_h = 31
    max_lines = max(1, (y + h - ty - 24) // line_h)
    if len(body_lines) > max_lines:
        body_lines = wrapped(body, chars + 6)
        line_h = 27
        max_lines = max(1, (y + h - ty - 22) // line_h)
    if len(body_lines) > max_lines:
        body_lines = body_lines[:max_lines]
        body_lines[-1] = body_lines[-1][: max(0, len(body_lines[-1]) - 3)].rstrip() + "..."
    fnt = SMALL if line_h == 31 else TINY
    for line in body_lines:
        draw.text((x + 30, ty), line, fill=MUTED, font=fnt)
        ty += line_h


def bullet(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str = BLUE_D, chars: int = 92) -> int:
    draw.ellipse((x, y + 10, x + 14, y + 24), fill=color)
    ty = y
    for line in wrapped(text, chars):
        draw.text((x + 30, ty), line, fill=INK, font=BODY)
        ty += 34
    return ty + 12


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str = LINE) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=color, width=5)
    draw.polygon([(x2, y2), (x2 - 18, y2 - 12), (x2 - 18, y2 + 12)], fill=color)


def page_overview() -> Image.Image:
    img, draw = canvas(
        "AEGIS Backend + AI Next Steps",
        "Roadmap from local MVP to integrated Android product, analyst workflow, real AI, and production hardening.",
    )
    draw.text((110, 250), "Current baseline", fill=INK, font=H1)
    y = 320
    baseline = [
        ("FastAPI backend with SQLite local database and raw JSON payload storage.", BLUE_D),
        ("Schema validation, body-token auth, idempotent ingestion, and processing status tracking.", GREEN_D),
        ("Normalization for device posture, app inventory, and redacted important logs.", CYAN_D),
        ("Deterministic risk scoring plus audited AI/LLM stub for high-risk evidence review.", PURPLE_D),
        ("Analyst feedback endpoint and Docker Compose path for production-style services.", RED_D),
    ]
    for text, color in baseline:
        y = bullet(draw, 135, y, text, color=color, chars=125)

    cards = [
        ((110, 750), (415, 300), "1. Android", "Connect real agent uploads to POST /api/v1/telemetry and verify end-to-end processing.", BLUE, BLUE_D),
        ((570, 750), (415, 300), "2. Dashboard", "Add a minimal analyst UI for latest risk, timeline, payload summary, logs, and feedback.", GREEN, GREEN_D),
        ((1030, 750), (415, 300), "3. Rules", "Tune deterministic scoring using real safe, suspicious, and critical device examples.", YELLOW, YELLOW_D),
        ((1490, 750), (415, 300), "4. Real AI", "Add a provider behind the LLMAnalyzer interface with strict JSON and evidence references.", PURPLE, PURPLE_D),
        ((1950, 750), (330, 300), "5. Harden", "Move to Postgres, Redis queue, migrations, stronger auth, metrics, and retention.", RED, RED_D),
    ]
    for item in cards:
        card(draw, *item, chars=28)
    for x in [525, 985, 1445, 1905]:
        arrow(draw, (x, 900), (x + 45, 900))

    draw.text((120, 1230), "Guiding principle", fill=INK, font=H1)
    y = 1305
    for text in [
        "Keep backend validation, storage, and risk state deterministic.",
        "Use AI to explain suspicious evidence and assist analysts, not to replace system truth.",
        "Add production infrastructure only after integration behavior is stable.",
    ]:
        y = bullet(draw, 145, y, text, color=PURPLE_D, chars=120)
    return img


def page_phase_1_2() -> Image.Image:
    img, draw = canvas(
        "Phase 1 And 2",
        "First connect the real Android data path, then give analysts a simple place to inspect it.",
    )
    card(
        draw,
        (110, 255),
        (980, 1020),
        "Phase 1 - Connect Android Agent",
        "Configure the agent backend URL. Send real scans to POST /api/v1/telemetry. Confirm 202 responses, duplicate handling, raw JSON files, normalized rows, and latest risk lookup. The exit goal is one real device completing scan, upload, processing, and risk review.",
        BLUE,
        BLUE_D,
        chars=56,
    )
    y = 510
    for text in [
        "Use the current Android payload unchanged.",
        "Keep enrollment_token body auth for compatibility.",
        "Verify raw payloads before debugging worker behavior.",
        "Test both clean and suspicious devices.",
        "Save sample payloads as fixtures for backend tests.",
    ]:
        y = bullet(draw, 165, y, text, color=BLUE_D, chars=55)

    card(
        draw,
        (1310, 255),
        (980, 1020),
        "Phase 2 - Minimal Analyst Dashboard",
        "Build a small operational dashboard over the existing API. It should show device risk, timeline, payload summaries, important logs, and analyst feedback. Avoid heavy product features until the evidence flow feels right.",
        GREEN,
        GREEN_D,
        chars=56,
    )
    y = 510
    for text in [
        "Device list sorted by latest risk.",
        "Device detail page with timeline records.",
        "Payload detail with normalized summary.",
        "Redacted logs with message hash references.",
        "Feedback form for true positive, false positive, benign, or needs more data.",
    ]:
        y = bullet(draw, 1365, y, text, color=GREEN_D, chars=55)

    draw.text((120, 1370), "Exit criteria", fill=INK, font=H1)
    draw.text((420, 1376), "A real device can upload telemetry, and an analyst can review the resulting risk in the UI.", fill=MUTED, font=BODY)
    return img


def page_phase_3_4() -> Image.Image:
    img, draw = canvas(
        "Phase 3 And 4",
        "Improve deterministic rules first, then connect real LLM providers through the existing safe interface.",
    )
    card(
        draw,
        (110, 255),
        (980, 1020),
        "Phase 3 - Improve Rules With Real Data",
        "Use safe, suspicious, and critical telemetry from real devices to tune rule scoring. Rules should stay explainable and covered by tests. This gives the AI layer better evidence and keeps the product reliable.",
        YELLOW,
        YELLOW_D,
        chars=56,
    )
    y = 510
    for text in [
        "Create fixtures from real uploaded payloads.",
        "Tune scores for root, integrity failure, patch age, bootloader state, and sideloaded sensitive apps.",
        "Add reasons that are readable by analysts.",
        "Track obvious false positives and adjust thresholds.",
        "Keep expected risk outputs in tests.",
    ]:
        y = bullet(draw, 165, y, text, color=YELLOW_D, chars=55)

    card(
        draw,
        (1310, 255),
        (980, 1020),
        "Phase 4 - Add Real AI Provider",
        "Keep the LLMAnalyzer interface. Add provider settings, timeout policy, structured JSON enforcement, redaction checks, and evidence-reference validation. Model output is advisory and audited.",
        PURPLE,
        PURPLE_D,
        chars=56,
    )
    y = 510
    for text in [
        "Call AI only for suspicious or high-risk cases.",
        "Send redacted evidence bundles, never raw secrets.",
        "Reject findings without evidence references.",
        "Store every attempt in ai_model_runs.",
        "Compare provider outputs against analyst_feedback later.",
    ]:
        y = bullet(draw, 1365, y, text, color=PURPLE_D, chars=55)

    draw.text((120, 1370), "Exit criteria", fill=INK, font=H1)
    draw.text((420, 1376), "Risk labels are stable, and high-risk cases can produce audited AI findings safely.", fill=MUTED, font=BODY)
    return img


def page_phase_5() -> Image.Image:
    img, draw = canvas(
        "Phase 5 - Production Hardening",
        "Move from local MVP behavior to a deployable service without changing the core data contracts.",
    )
    cards = [
        ((110, 250), (650, 330), "Data Layer", "Make Postgres the production default, add Alembic migrations, define retention, and document backup/restore.", BLUE, BLUE_D),
        ((875, 250), (650, 330), "Queue + Worker", "Use Redis/RQ, Celery, or equivalent. API accepts payloads quickly; worker handles normalization, scoring, and AI runs.", GREEN, GREEN_D),
        ((1640, 250), (650, 330), "Auth + Integrity", "Move from body token to bearer auth, then mTLS later. Add Play Integrity backend challenge/decode flow.", YELLOW, YELLOW_D),
        ((110, 700), (650, 330), "Observability", "Add request logs, processing metrics, failed payload alerts, model-run errors, and dashboard health checks.", CYAN, CYAN_D),
        ((875, 700), (650, 330), "Security", "Protect raw telemetry, enforce redaction before AI calls, rotate secrets, and separate dev/prod settings.", RED, RED_D),
        ((1640, 700), (650, 330), "Release Path", "Use Docker Compose first, then cloud deployment after API, worker, database, and queue behavior is stable.", PURPLE, PURPLE_D),
    ]
    for item in cards:
        card(draw, *item, chars=42)

    draw.text((120, 1195), "Production readiness checklist", fill=INK, font=H1)
    y = 1270
    checklist = [
        "Postgres migrations run cleanly from an empty database.",
        "Worker retries failed payloads safely and marks permanent failures clearly.",
        "Auth no longer depends on body enrollment_token for production clients.",
        "AI provider can be disabled without breaking risk scoring.",
        "Backups and telemetry retention are documented before real user data is stored.",
    ]
    for text in checklist:
        y = bullet(draw, 145, y, text, color=RED_D, chars=120)
    return img


def page_timeline() -> Image.Image:
    img, draw = canvas(
        "Suggested Execution Order",
        "Small steps, each with a concrete demo result before moving deeper into infrastructure.",
    )
    phases = [
        ("Week 1", "Android upload integration", BLUE, BLUE_D),
        ("Week 2", "Analyst dashboard MVP", GREEN, GREEN_D),
        ("Week 3", "Rule tuning with fixtures", YELLOW, YELLOW_D),
        ("Week 4", "Real AI provider pilot", PURPLE, PURPLE_D),
        ("Week 5+", "Production hardening", RED, RED_D),
    ]
    x = 180
    y = 330
    prev = None
    for label, title, fill, outline in phases:
        draw.ellipse((x, y, x + 150, y + 150), fill=fill, outline=outline, width=4)
        draw.text((x + 37, y + 38), label, fill=INK, font=SMALL)
        draw.text((x - 45, y + 185), title, fill=INK, font=SMALL)
        if prev:
            arrow(draw, prev, (x, y + 75))
        prev = (x + 150, y + 75)
        x += 430

    draw.text((120, 720), "Do next, immediately", fill=INK, font=H1)
    y = 795
    immediate = [
        "Pick one Android device and point uploads to http://127.0.0.1:8080/api/v1/telemetry.",
        "Capture one clean payload and one suspicious/high-risk payload.",
        "Turn those payloads into backend test fixtures.",
        "Build the first dashboard screen: device list with latest risk.",
        "Use feedback labels to measure rule quality before trusting real AI output.",
    ]
    for text in immediate:
        y = bullet(draw, 145, y, text, color=BLUE_D, chars=120)

    draw.rounded_rectangle((130, 1245, 2270, 1450), radius=20, fill=WHITE, outline="#d8e0eb", width=3)
    draw.text((165, 1280), "Decision checkpoint", fill=INK, font=H1)
    draw.text(
        (165, 1350),
        "After the dashboard can review real device telemetry, decide whether to invest next in rule quality, real AI, or production deployment.",
        fill=MUTED,
        font=BODY,
    )
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = [
        ("01-roadmap-overview.png", page_overview()),
        ("02-android-and-dashboard.png", page_phase_1_2()),
        ("03-rules-and-ai.png", page_phase_3_4()),
        ("04-production-hardening.png", page_phase_5()),
        ("05-execution-order.png", page_timeline()),
    ]
    saved: list[Path] = []
    for name, image in pages:
        path = OUT_DIR / name
        image.save(path)
        saved.append(path)

    pdf_pages = [Image.open(path).convert("RGB") for path in saved]
    pdf_pages[0].save(PDF_PATH, "PDF", save_all=True, append_images=pdf_pages[1:], resolution=144.0)
    print(f"Wrote {PDF_PATH}")
    for path in saved:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
