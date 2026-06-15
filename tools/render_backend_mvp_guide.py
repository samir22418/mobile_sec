from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "generated" / "backend-mvp-guide"
PDF_PATH = ROOT / "docs" / "backend-mvp-comprehensive-guide.pdf"

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
H2 = font(30, True)
BODY = font(25)
SMALL = font(22)
TINY = font(19)
CODE = font(21)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrapped(text: str, chars: int) -> list[str]:
    result: list[str] = []
    for line in text.split("\n"):
        result.extend(wrap(line, width=chars) or [""])
    return result


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((80, 54), title, fill=INK, font=TITLE)
    draw.text((82, 126), subtitle, fill=MUTED, font=SUBTITLE)
    draw.line((80, 176, W - 80, 176), fill="#d9e1ec", width=3)
    return img, draw


def box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    size: tuple[int, int],
    title: str,
    body: str,
    fill: str,
    accent: str,
    body_chars: int = 30,
) -> None:
    x, y = xy
    w, h = size
    draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=WHITE, outline="#d8e0eb", width=3)
    draw.rounded_rectangle((x, y, x + w, y + 16), radius=18, fill=accent)
    draw.rectangle((x, y + 8, x + w, y + 16), fill=accent)
    draw.rounded_rectangle((x + 22, y + 32, x + 78, y + 88), radius=14, fill=fill, outline=accent, width=2)
    draw.text((x + 96, y + 34), title, fill=INK, font=H2)
    ty = y + 100
    body_lines = wrapped(body, body_chars)
    body_font = SMALL
    line_h = 31
    max_lines = max(1, (y + h - ty - 22) // line_h)
    if len(body_lines) > max_lines:
        body_font = TINY
        line_h = 26
        body_lines = wrapped(body, body_chars + 5)
        max_lines = max(1, (y + h - ty - 20) // line_h)
    if len(body_lines) > max_lines:
        body_lines = body_lines[:max_lines]
        last = body_lines[-1]
        body_lines[-1] = f"{last[: max(0, len(last) - 3)].rstrip()}..."
    for line in body_lines:
        draw.text((x + 28, ty), line, fill=MUTED, font=body_font)
        ty += line_h


def bullet(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str = BLUE_D, chars: int = 82) -> int:
    draw.ellipse((x, y + 10, x + 14, y + 24), fill=color)
    ty = y
    for line in wrapped(text, chars):
        draw.text((x + 28, ty), line, fill=INK, font=BODY)
        ty += 34
    return ty + 12


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str = LINE) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=color, width=5)
    if x2 >= x1:
        pts = [(x2, y2), (x2 - 18, y2 - 12), (x2 - 18, y2 + 12)]
    else:
        pts = [(x2, y2), (x2 + 18, y2 - 12), (x2 + 18, y2 + 12)]
    draw.polygon(pts, fill=color)


def label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, outline: str) -> None:
    x, y = xy
    tw, th = text_size(draw, text, SMALL)
    draw.rounded_rectangle((x, y, x + tw + 30, y + th + 18), radius=20, fill=fill, outline=outline, width=2)
    draw.text((x + 15, y + 8), text, fill=INK, font=SMALL)


def page_summary() -> Image.Image:
    img, draw = canvas(
        "AEGIS Backend MVP - Comprehensive Guide",
        "Simple local backend with telemetry ingestion, normalized data, deterministic risk, and an audited AI stub.",
    )
    boxes = [
        ((90, 250), (510, 250), "API Service", "FastAPI accepts Android telemetry, checks the enrollment token, validates schema v1, and returns 202 for accepted payloads.", BLUE, BLUE_D),
        ((650, 250), (510, 250), "Storage", "SQLite is the local default. Raw payload JSON is kept on disk before processing for audit and replay.", GREEN, GREEN_D),
        ((1210, 250), (510, 250), "Worker", "Inline processing works locally. The same status fields can support a queue worker later.", CYAN, CYAN_D),
        ((1770, 250), (510, 250), "Risk + AI", "Rules produce the source of truth. The LLM analyzer is a structured, audited stub for high-risk cases.", PURPLE, PURPLE_D),
    ]
    for item in boxes:
        box(draw, *item)

    draw.text((110, 600), "What I made", fill=INK, font=H1)
    y = 670
    for text, color in [
        ("Created a new Python backend under backend/ using FastAPI, SQLAlchemy, pytest, and app settings.", BLUE_D),
        ("Copied the existing Android telemetry schema into the backend and validate every incoming payload against it.", GREEN_D),
        ("Implemented idempotent ingestion by payload_id, raw JSON storage, and local processing status tracking.", CYAN_D),
        ("Normalized device posture, current app inventory, and redacted important logs into queryable tables.", YELLOW_D),
        ("Added deterministic risk scoring plus an LLMAnalyzer stub that only runs for suspicious/high-risk findings.", PURPLE_D),
        ("Exposed the MVP API endpoints for latest risk, timelines, payload lookup, and analyst feedback.", RED_D),
    ]:
        y = bullet(draw, 130, y, text, color=color, chars=120)

    label(draw, (130, 1320), "Verified: pytest 17 passed", GREEN, GREEN_D)
    label(draw, (500, 1320), "Verified: /health OK", BLUE, BLUE_D)
    label(draw, (815, 1320), "Verified: telemetry smoke processed", PURPLE, PURPLE_D)
    return img


def page_architecture() -> Image.Image:
    img, draw = canvas(
        "Runtime Architecture",
        "The MVP keeps the backend small: API, database, raw store, local worker, rules, and AI audit trail.",
    )
    steps = [
        ((90, 270), (330, 190), "Android Agent", "Sends current telemetry payload unchanged.", BLUE, BLUE_D),
        ((505, 270), (330, 190), "FastAPI", "Health, ingestion, risk, timeline, and feedback APIs.", GREEN, GREEN_D),
        ((920, 270), (330, 190), "Auth + Schema", "Body token now; schema v1 validation at the edge.", YELLOW, YELLOW_D),
        ((1335, 270), (330, 190), "Raw Store", "JSON saved before processing for auditability.", CYAN, CYAN_D),
        ((1750, 270), (330, 190), "SQLAlchemy DB", "SQLite locally; Postgres-compatible models.", PURPLE, PURPLE_D),
    ]
    for item in steps:
        box(draw, *item, body_chars=25)
    for x in [420, 835, 1250, 1665]:
        arrow(draw, (x, 365), (x + 80, 365))

    lower = [
        ((210, 760), (420, 230), "Normalization Worker", "Processes accepted payloads into device_reports, app_inventory_current, and important_logs.", CYAN, CYAN_D),
        ((785, 760), (420, 230), "Rule Scoring", "Calculates risk_score, label, confidence, reasons, action, and review flag.", RED, RED_D),
        ((1360, 760), (420, 230), "LLM Stub", "Runs only for high-risk cases and records structured AI model runs.", PURPLE, PURPLE_D),
        ((1850, 760), (420, 230), "Analyst/API Views", "Latest risk, timeline, payload status, and feedback loop.", GREEN, GREEN_D),
    ]
    for item in lower:
        box(draw, *item, body_chars=34)
    arrow(draw, (1915, 465), (420, 760))
    arrow(draw, (630, 875), (785, 875))
    arrow(draw, (1205, 875), (1360, 875))
    arrow(draw, (1780, 875), (1850, 875))

    draw.text((120, 1190), "AI boundary", fill=INK, font=H1)
    y = 1265
    for text in [
        "AI never validates the payload, mutates device state, or overrides deterministic storage decisions.",
        "AI receives a redacted evidence bundle and must return structured JSON with evidence references.",
        "Every model attempt is written to ai_model_runs for audit, debugging, and future provider comparison.",
    ]:
        y = bullet(draw, 145, y, text, color=PURPLE_D, chars=120)
    return img


def page_data_api() -> Image.Image:
    img, draw = canvas(
        "Data Model And Public API",
        "The tables are intentionally boring and queryable; the API exposes only what the agent and analysts need now.",
    )
    tables = [
        ((95, 250), (510, 300), "telemetry_payloads", "payload_id, device_id, scan_id, raw_path, processing_status, processing_error, received_at", BLUE, BLUE_D),
        ((650, 250), (510, 300), "device_reports", "device posture snapshot: root signals, integrity verdict, patch date, bootloader state", GREEN, GREEN_D),
        ((1205, 250), (510, 300), "app_inventory_current", "latest known app state by device and package, including source and permissions", CYAN, CYAN_D),
        ((1760, 250), (510, 300), "important_logs", "redacted log message, message hash, level, tag, matched rule", YELLOW, YELLOW_D),
        ((375, 690), (510, 300), "risk_assessments", "risk_score, risk_label, confidence, reasons_json, recommended_action, review flag", RED, RED_D),
        ((945, 690), (510, 300), "ai_model_runs", "provider, model, prompt/evidence hash, output_json, status, error", PURPLE, PURPLE_D),
        ((1515, 690), (510, 300), "analyst_feedback", "finding id, label, notes, analyst id, created_at for future evaluation", GREEN, GREEN_D),
    ]
    for item in tables:
        box(draw, *item, body_chars=34)

    draw.text((120, 1135), "Public interfaces", fill=INK, font=H1)
    endpoints = [
        "GET /health",
        "POST /api/v1/telemetry",
        "GET /api/v1/devices/{device_id}/latest-risk",
        "GET /api/v1/devices/{device_id}/timeline",
        "GET /api/v1/payloads/{payload_id}",
        "POST /api/v1/findings/{finding_id}/feedback",
    ]
    x, y = 130, 1210
    for idx, endpoint in enumerate(endpoints):
        label(draw, (x, y), endpoint, GRAY if idx % 2 else BLUE, GRAY_D if idx % 2 else BLUE_D)
        y += 66
        if idx == 2:
            x, y = 1080, 1210
    return img


def page_run_test() -> Image.Image:
    img, draw = canvas(
        "Run And Test Guide",
        "Local commands for the MVP backend, plus the smoke test result from this run.",
    )
    sections = [
        ((95, 245), (700, 420), "1. Run the API", "cd C:\\Users\\ASUS\\Desktop\\mobile_sec\\backend\npython -m uvicorn app.main:app --host 127.0.0.1 --port 8080\n\nHealth URL:\nhttp://127.0.0.1:8080/health", BLUE, BLUE_D),
        ((850, 245), (700, 420), "2. Run tests", "cd C:\\Users\\ASUS\\Desktop\\mobile_sec\\backend\npython -m pytest\n\nCurrent result:\n17 passed", GREEN, GREEN_D),
        ((1605, 245), (700, 420), "3. Optional worker", "Inline processing is enabled locally.\n\nFor queue-style operation:\npython -m app.worker --once\npython -m app.worker", CYAN, CYAN_D),
    ]
    for item in sections:
        box(draw, *item, body_chars=48)

    draw.text((120, 790), "Smoke test performed", fill=INK, font=H1)
    smoke = [
        ("POST /api/v1/telemetry", "accepted=true, duplicate=false, processing_status=PROCESSED"),
        ("GET /api/v1/devices/sample-device-001/latest-risk", "risk_score=100, risk_label=Critical, needs_human_review=true"),
        ("GET /api/v1/payloads/manual-smoke-001", "processing_status=PROCESSED and risk summary returned"),
    ]
    y = 870
    for title, detail in smoke:
        draw.rounded_rectangle((130, y, 2270, y + 112), radius=16, fill=WHITE, outline="#d8e0eb", width=3)
        draw.text((160, y + 20), title, fill=INK, font=H2)
        draw.text((160, y + 63), detail, fill=MUTED, font=BODY)
        y += 145

    draw.text((120, 1340), "Local defaults", fill=INK, font=H1)
    label(draw, (130, 1410), "DB: backend-data/aegis.db", YELLOW, YELLOW_D)
    label(draw, (530, 1410), "Raw JSON: backend-data/raw-payloads", PURPLE, PURPLE_D)
    label(draw, (1045, 1410), "Token: sample-token", GREEN, GREEN_D)
    return img


def page_ai_phases() -> Image.Image:
    img, draw = canvas(
        "AI-Aware Maturity Path",
        "AI is important, but the first version keeps it constrained, testable, and easy to replace.",
    )
    phases = [
        ("Phase 0", "Backend skeleton", BLUE, BLUE_D),
        ("Phase 1", "Ingestion", GREEN, GREEN_D),
        ("Phase 2", "Normalization", CYAN, CYAN_D),
        ("Phase 3", "Rule scoring", RED, RED_D),
        ("Phase 4", "AI evidence + LLM stub", PURPLE, PURPLE_D),
        ("Phase 5", "Analyst feedback", YELLOW, YELLOW_D),
        ("Phase 6", "Production hardening", GRAY, GRAY_D),
    ]
    x, y = 130, 275
    prev: tuple[int, int] | None = None
    for index, (phase, title, fill, outline) in enumerate(phases):
        cx = x + index * 315
        draw.ellipse((cx, y, cx + 150, y + 150), fill=fill, outline=outline, width=4)
        draw.text((cx + 31, y + 42), phase, fill=INK, font=SMALL)
        draw.text((cx - 35, y + 175), title, fill=INK, font=SMALL)
        if prev:
            arrow(draw, prev, (cx, y + 75))
        prev = (cx + 150, y + 75)

    columns = [
        ((130, 660), (640, 620), "Now", "Local MVP is implemented. It validates telemetry, stores raw payloads, normalizes data, scores risk, records AI stub runs, and accepts analyst feedback.", GREEN, GREEN_D),
        ((880, 660), (640, 620), "Next", "Connect real Android uploads to this backend, add dashboard views, and use analyst feedback to tune rule thresholds before adding a real LLM provider.", BLUE, BLUE_D),
        ((1630, 660), (640, 620), "Later", "Docker Compose already sketches API, worker, Postgres, and Redis. Bearer auth, mTLS, Play Integrity backend decode, and real model providers can be swapped in behind existing interfaces.", PURPLE, PURPLE_D),
    ]
    for item in columns:
        box(draw, *item, body_chars=45)

    y = 1360
    for text in [
        "Keep deterministic rules as the authoritative decision layer.",
        "Use LLMs for explanation, evidence grouping, and analyst assistance after redaction.",
        "Evaluate future providers by comparing ai_model_runs against analyst_feedback labels.",
    ]:
        y = bullet(draw, 150, y, text, color=PURPLE_D, chars=120)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = [
        ("01-title-and-summary.png", page_summary()),
        ("02-runtime-architecture.png", page_architecture()),
        ("03-data-model-and-api.png", page_data_api()),
        ("04-run-and-test-guide.png", page_run_test()),
        ("05-ai-maturity-path.png", page_ai_phases()),
    ]

    saved: list[Path] = []
    for filename, image in pages:
        path = OUT_DIR / filename
        image.save(path)
        saved.append(path)

    rgb_pages = [Image.open(path).convert("RGB") for path in saved]
    rgb_pages[0].save(PDF_PATH, save_all=True, append_images=rgb_pages[1:])

    print(f"Wrote {PDF_PATH}")
    for path in saved:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
