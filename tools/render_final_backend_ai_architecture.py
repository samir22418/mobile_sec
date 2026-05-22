from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "generated" / "final-backend-ai-architecture"
PDF_PATH = ROOT / "docs" / "final-backend-ai-architecture.pdf"

W = 2400
H = 1600

BG = "#f7f9fc"
INK = "#182033"
MUTED = "#617089"
LINE = "#7b8799"
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
WHITE = "#ffffff"


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


TITLE_FONT = font(52, True)
SUBTITLE_FONT = font(25)
NODE_FONT = font(30, True)
SMALL_FONT = font(23)
TINY_FONT = font(19)


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((80, 54), title, fill=INK, font=TITLE_FONT)
    draw.text((82, 122), subtitle, fill=MUTED, font=SUBTITLE_FONT)
    return img, draw


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def lines(text: str, width: int) -> list[str]:
    out: list[str] = []
    for part in text.split("\n"):
        out.extend(wrap(part, width=width) or [""])
    return out


def node(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    size: tuple[int, int],
    text: str,
    fill: str,
    border: str,
    max_chars: int = 18,
    fnt: ImageFont.ImageFont = NODE_FONT,
) -> tuple[int, int, int, int]:
    x, y = xy
    w, h = size
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=fill, outline=border, width=4)
    text_lines = lines(text, max_chars)
    line_h = text_size(draw, "Ag", fnt)[1] + 9
    total_h = line_h * len(text_lines)
    ty = y + (h - total_h) // 2
    for line in text_lines:
        tw, _ = text_size(draw, line, fnt)
        draw.text((x + (w - tw) // 2, ty), line, fill=INK, font=fnt)
        ty += line_h
    return x, y, x + w, y + h


def note(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    size: tuple[int, int],
    title: str,
    body: list[str],
    color: str,
) -> tuple[int, int, int, int]:
    x, y = xy
    w, h = size
    box = (x, y, x + w, y + h)
    draw.rounded_rectangle(box, radius=24, fill=WHITE, outline=color, width=4)
    draw.text((x + 28, y + 26), title, fill=INK, font=NODE_FONT)
    ty = y + 92
    for item in body:
        draw.text((x + 28, ty), f"- {item}", fill=MUTED, font=SMALL_FONT)
        ty += 38
    return box


def center(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = box
    return (x1 + x2) // 2, (y1 + y2) // 2


def edge(box: tuple[int, int, int, int], side: str) -> tuple[int, int]:
    x1, y1, x2, y2 = box
    if side == "r":
        return x2, (y1 + y2) // 2
    if side == "l":
        return x1, (y1 + y2) // 2
    if side == "t":
        return (x1 + x2) // 2, y1
    return (x1 + x2) // 2, y2


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = LINE,
    width: int = 5,
    elbow: tuple[int, int] | None = None,
) -> None:
    pts = [start]
    if elbow:
        pts.append(elbow)
    pts.append(end)
    draw.line(pts, fill=color, width=width, joint="curve")
    sx, sy = pts[-2]
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    if abs(dx) >= abs(dy):
        tri = [(ex, ey), (ex - 18 if dx >= 0 else ex + 18, ey - 10), (ex - 18 if dx >= 0 else ex + 18, ey + 10)]
    else:
        tri = [(ex, ey), (ex - 10, ey - 18 if dy >= 0 else ey + 18), (ex + 10, ey - 18 if dy >= 0 else ey + 18)]
    draw.polygon(tri, fill=color)


def save(img: Image.Image, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    img.save(path, "PNG", optimize=True)
    return path


def chart_overview() -> Path:
    img, d = canvas(
        "AEGIS Final Backend + AI Architecture",
        "Simple production backend with AI used only where it adds security value",
    )

    agent = node(d, (80, 420), (270, 115), "Android Agent", BLUE, BLUE_D)
    api = node(d, (455, 420), (300, 115), "Ingestion API", BLUE, BLUE_D)
    raw = node(d, (845, 275), (300, 105), "Raw Payload Store", GRAY, GRAY_D)
    queue = node(d, (845, 565), (300, 105), "Processing Queue", YELLOW, YELLOW_D)
    worker = node(d, (1240, 420), (300, 115), "Telemetry Worker", GREEN, GREEN_D)
    db = node(d, (1630, 275), (300, 105), "PostgreSQL State", CYAN, CYAN_D)
    risk = node(d, (1630, 565), (300, 105), "Risk + AI Engine", PURPLE, PURPLE_D)
    assess = node(d, (2020, 420), (300, 115), "Risk Assessments", RED, RED_D)
    dash = node(d, (2020, 765), (300, 115), "Dashboard / Alerts / API", CYAN, CYAN_D, max_chars=18)

    for a, b in [(agent, api), (api, raw), (api, queue), (queue, worker), (worker, db), (worker, risk), (risk, assess), (assess, dash)]:
        arrow(d, edge(a, "r"), edge(b, "l"))
    arrow(d, edge(raw, "r"), edge(worker, "l"), elbow=(1170, 327))
    arrow(d, edge(db, "r"), edge(assess, "l"), elbow=(1980, 327))

    note(d, (455, 1010), (430, 255), "Ingestion stays simple", ["auth", "schema validation", "idempotency", "raw storage"], BLUE_D)
    note(d, (990, 1010), (430, 255), "Worker does processing", ["normalize telemetry", "redact logs", "extract features", "update state"], GREEN_D)
    note(d, (1525, 1010), (430, 255), "AI is controlled", ["rules first", "LLM only if needed", "evidence required", "auditable outputs"], PURPLE_D)

    return save(img, "01-final-backend-overview.png")


def chart_flow() -> Path:
    img, d = canvas(
        "Final Processing Flow",
        "From agent upload to final risk assessment",
    )

    boxes = [
        ("Upload", BLUE, BLUE_D),
        ("Validate + Idempotency", BLUE, BLUE_D),
        ("Store Raw Payload", GRAY, GRAY_D),
        ("Normalize", GREEN, GREEN_D),
        ("Redact Logs", GREEN, GREEN_D),
        ("Extract Features", YELLOW, YELLOW_D),
        ("Rules + AI", PURPLE, PURPLE_D),
        ("Final Assessment", RED, RED_D),
    ]
    coords: list[tuple[int, int, int, int]] = []
    x = 95
    for label, fill, border in boxes:
        coords.append(node(d, (x, 510), (250, 130), label, fill, border, max_chars=15))
        x += 285
    for a, b in zip(coords, coords[1:]):
        arrow(d, edge(a, "r"), edge(b, "l"))

    note(d, (180, 850), (500, 270), "Reliability", ["same payload_id is safe to retry", "raw payload is kept for replay", "worker can reprocess later"], BLUE_D)
    note(d, (950, 850), (500, 270), "Data engineering", ["posture/app/log normalization", "latest app state", "compact feature vector"], GREEN_D)
    note(d, (1715, 850), (500, 270), "AI result", ["score", "reasons", "confidence", "recommended action"], RED_D)

    return save(img, "02-final-processing-flow.png")


def chart_ai() -> Path:
    img, d = canvas(
        "Simple Risk + AI Decision Flow",
        "Rules always run; LLMs run only for suspicious or ambiguous cases",
    )

    features = node(d, (1000, 210), (400, 100), "Features + Redacted Evidence", YELLOW, YELLOW_D, max_chars=22)
    rules = node(d, (1025, 410), (350, 100), "Rule Engine", GREEN, GREEN_D)
    decision = node(d, (1025, 620), (350, 100), "Suspicious?", PURPLE, PURPLE_D)
    low = node(d, (470, 850), (380, 115), "Store Low-Risk Assessment", CYAN, CYAN_D, max_chars=19)
    llm = node(d, (1035, 850), (330, 115), "Primary LLM Analyst", PURPLE, PURPLE_D)
    critical = node(d, (1025, 1090), (350, 100), "Critical or Ambiguous?", PURPLE, PURPLE_D, max_chars=18)
    reviewer = node(d, (1525, 1090), (350, 100), "Reviewer LLM", PURPLE, PURPLE_D)
    fusion = node(d, (1025, 1300), (350, 105), "Evidence Fusion", RED, RED_D)
    final = node(d, (1525, 1300), (350, 105), "Final Risk + Reasons", RED, RED_D, max_chars=17)

    arrow(d, edge(features, "b"), edge(rules, "t"))
    arrow(d, edge(rules, "b"), edge(decision, "t"))
    arrow(d, edge(decision, "l"), edge(low, "t"), elbow=(660, 670))
    d.text((725, 705), "No", fill=GREEN_D, font=SMALL_FONT)
    arrow(d, edge(decision, "b"), edge(llm, "t"))
    d.text((1230, 760), "Yes", fill=PURPLE_D, font=SMALL_FONT)
    arrow(d, edge(llm, "b"), edge(critical, "t"))
    arrow(d, edge(critical, "r"), edge(reviewer, "l"))
    d.text((1425, 1120), "Yes", fill=RED_D, font=SMALL_FONT)
    arrow(d, edge(critical, "b"), edge(fusion, "t"))
    d.text((1225, 1225), "No", fill=GREEN_D, font=SMALL_FONT)
    arrow(d, edge(reviewer, "b"), edge(final, "t"))
    arrow(d, edge(fusion, "r"), edge(final, "l"))
    arrow(d, edge(low, "r"), edge(final, "l"), elbow=(1480, 920))

    note(d, (120, 210), (520, 300), "LLM guardrails", ["redacted input only", "structured JSON output", "must cite evidence", "cannot execute actions"], PURPLE_D)
    note(d, (1725, 210), (520, 300), "Why this is simple", ["rules handle normal cases", "LLM handles only useful cases", "reviewer only for critical cases"], GREEN_D)

    return save(img, "03-simple-risk-ai-flow.png")


def chart_data() -> Path:
    img, d = canvas(
        "Minimal Backend Data Model",
        "Small first schema that still supports replay, scoring, AI audit, and feedback",
    )

    payloads = node(d, (120, 690), (330, 100), "telemetry_payloads", BLUE, BLUE_D)
    device = node(d, (590, 400), (310, 95), "device_reports", GREEN, GREEN_D)
    apps = node(d, (590, 690), (310, 95), "app_inventory_current", GREEN, GREEN_D, max_chars=18)
    logs = node(d, (590, 980), (310, 95), "important_logs", GREEN, GREEN_D)
    risk = node(d, (1060, 690), (330, 105), "risk_assessments", RED, RED_D)
    runs = node(d, (1530, 520), (310, 95), "ai_model_runs", PURPLE, PURPLE_D)
    feedback = node(d, (1530, 860), (310, 95), "analyst_feedback", PURPLE, PURPLE_D)
    devices = node(d, (1980, 520), (280, 95), "devices", CYAN, CYAN_D)
    enroll = node(d, (1980, 860), (280, 95), "enrollments", CYAN, CYAN_D)

    for b in [device, apps, logs]:
        arrow(d, edge(payloads, "r"), edge(b, "l"))
        arrow(d, edge(b, "r"), edge(risk, "l"))
    arrow(d, edge(risk, "r"), edge(runs, "l"))
    arrow(d, edge(risk, "r"), edge(feedback, "l"))
    arrow(d, edge(runs, "r"), edge(devices, "l"))
    arrow(d, edge(feedback, "r"), edge(enroll, "l"))

    note(d, (160, 1190), (600, 220), "Source of truth", ["telemetry_payloads owns payload_id idempotency", "raw payload URI supports replay"], BLUE_D)
    note(d, (910, 1190), (600, 220), "Security state", ["device posture", "latest app inventory", "redacted important logs"], GREEN_D)
    note(d, (1660, 1190), (600, 220), "Decision layer", ["risk score and reasons", "model audit trail", "analyst feedback"], RED_D)

    return save(img, "04-minimal-data-model.png")


def build_pdf(paths: list[Path]) -> None:
    pages = [Image.open(path).convert("RGB") for path in paths]
    pages[0].save(PDF_PATH, "PDF", save_all=True, append_images=pages[1:], resolution=144.0)


def main() -> None:
    paths = [
        chart_overview(),
        chart_flow(),
        chart_ai(),
        chart_data(),
    ]
    build_pdf(paths)
    print("Generated PNG charts:")
    for path in paths:
        print(path)
    print(f"Generated PDF:\n{PDF_PATH}")


if __name__ == "__main__":
    main()
