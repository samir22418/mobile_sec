from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "generated" / "ai-llm-charts"
PDF_PATH = ROOT / "docs" / "ai-llm-threat-analysis-charts.pdf"

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


TITLE_FONT = font(50, True)
SUBTITLE_FONT = font(24)
NODE_FONT = font(27, True)
SMALL_FONT = font(22)
TINY_FONT = font(18)


def canvas(title: str, subtitle: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((80, 48), title, fill=INK, font=TITLE_FONT)
    if subtitle:
        draw.text((82, 112), subtitle, fill=MUTED, font=SUBTITLE_FONT)
    return img, draw


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def fit_lines(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    for part in text.split("\n"):
        lines.extend(wrap(part, width=max_chars) or [""])
    return lines


def node(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    size: tuple[int, int],
    text: str,
    fill: str = WHITE,
    border: str = BLUE_D,
    text_fill: str = INK,
    radius: int = 22,
    fnt: ImageFont.ImageFont = NODE_FONT,
    max_chars: int = 18,
) -> tuple[int, int, int, int]:
    x, y = xy
    w, h = size
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=border, width=4)
    lines = fit_lines(text, max_chars)
    line_h = text_size(draw, "Ag", fnt)[1] + 8
    total_h = line_h * len(lines)
    ty = y + (h - total_h) // 2
    for line in lines:
        tw, _ = text_size(draw, line, fnt)
        draw.text((x + (w - tw) // 2, ty), line, fill=text_fill, font=fnt)
        ty += line_h
    return x, y, x + w, y + h


def label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str = MUTED) -> None:
    draw.text(xy, text, fill=fill, font=SMALL_FONT)


def center(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = box
    return (x1 + x2) // 2, (y1 + y2) // 2


def edge_point(box: tuple[int, int, int, int], side: str) -> tuple[int, int]:
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
    points = [start]
    if elbow:
        points.append(elbow)
    points.append(end)
    draw.line(points, fill=color, width=width, joint="curve")
    sx, sy = points[-2]
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    if abs(dx) >= abs(dy):
        if dx >= 0:
            tri = [(ex, ey), (ex - 18, ey - 10), (ex - 18, ey + 10)]
        else:
            tri = [(ex, ey), (ex + 18, ey - 10), (ex + 18, ey + 10)]
    else:
        if dy >= 0:
            tri = [(ex, ey), (ex - 10, ey - 18), (ex + 10, ey - 18)]
        else:
            tri = [(ex, ey), (ex - 10, ey + 18), (ex + 10, ey + 18)]
    draw.polygon(tri, fill=color)


def group(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, outline: str) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=30, outline=outline, width=4, fill=None)
    draw.rectangle((x1 + 28, y1 - 18, x1 + 28 + 18 * len(title), y1 + 20), fill=BG)
    draw.text((x1 + 36, y1 - 16), title, fill=outline, font=SMALL_FONT)


def save(img: Image.Image, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    img.save(path, "PNG", optimize=True)
    return path


def chart_overview() -> Path:
    img, d = canvas(
        "AEGIS AI/LLM Threat Analysis Overview",
        "Evidence-grounded malicious app, device posture, and log analysis",
    )

    group(d, (60, 185, 2280, 1465), "analysis pipeline", CYAN_D)

    ingest = node(d, (90, 360), (260, 110), "Android Agent Telemetry", BLUE, BLUE_D)
    api = node(d, (420, 360), (250, 110), "Telemetry Ingestion API", BLUE, BLUE_D)
    norm = node(d, (740, 290), (250, 100), "Normalize", GREEN, GREEN_D)
    redact = node(d, (740, 430), (250, 100), "Redact", GREEN, GREEN_D)
    enrich = node(d, (1060, 360), (250, 110), "Threat Intel + Policy Enrichment", GREEN, GREEN_D, max_chars=15)
    features = node(d, (1390, 360), (250, 110), "Feature Extraction", YELLOW, YELLOW_D)
    router = node(d, (1720, 360), (250, 110), "AI Model Router", PURPLE, PURPLE_D)
    fusion = node(d, (2040, 675), (250, 120), "Evidence Fusion", RED, RED_D)

    rules = node(d, (1260, 660), (260, 95), "Rule Engine", YELLOW, YELLOW_D)
    logm = node(d, (1640, 590), (280, 95), "Log Triage Model", PURPLE, PURPLE_D)
    appm = node(d, (1640, 720), (280, 95), "App Reputation Model", PURPLE, PURPLE_D)
    llm1 = node(d, (1640, 850), (280, 95), "Primary LLM Analyst", PURPLE, PURPLE_D)
    llm2 = node(d, (1640, 980), (280, 95), "Reviewer LLM", PURPLE, PURPLE_D)

    score = node(d, (2040, 935), (250, 95), "Risk Score", RED, RED_D)
    findings = node(d, (2040, 1065), (250, 95), "Evidence Findings", RED, RED_D)
    actions = node(d, (2040, 1195), (250, 95), "Recommended Actions", RED, RED_D)
    dashboard = node(d, (2040, 1325), (250, 95), "SOC Dashboard", CYAN, CYAN_D)

    for a, b in [(ingest, api), (api, norm), (api, redact), (norm, enrich), (redact, enrich), (enrich, features), (features, router)]:
        arrow(d, edge_point(a, "r"), edge_point(b, "l"))
    arrow(d, edge_point(features, "b"), edge_point(rules, "t"))
    bus_x = 1575
    bus_top = 530
    bus_bottom = center(llm2)[1]
    arrow(d, edge_point(router, "b"), (bus_x, bus_top), color=LINE)
    d.line((bus_x, bus_top, bus_x, bus_bottom), fill=LINE, width=5)
    for b in [logm, appm, llm1, llm2]:
        arrow(d, (bus_x, center(b)[1]), edge_point(b, "l"))
        arrow(d, edge_point(b, "r"), edge_point(fusion, "l"))
    arrow(d, edge_point(rules, "r"), edge_point(fusion, "l"), elbow=(1970, 707))
    out_bus_x = 2005
    out_bus_top = 850
    out_bus_bottom = center(dashboard)[1]
    arrow(d, edge_point(fusion, "b"), (out_bus_x, out_bus_top), color=LINE)
    d.line((out_bus_x, out_bus_top, out_bus_x, out_bus_bottom), fill=LINE, width=5)
    for b in [score, findings, actions, dashboard]:
        arrow(d, (out_bus_x, center(b)[1]), edge_point(b, "l"))

    label(d, (95, 1420), "LLMs run after validation, redaction, enrichment, and feature extraction.")
    return save(img, "01-ai-analysis-overview.png")


def chart_router() -> Path:
    img, d = canvas(
        "Model Router Decision Chart",
        "Choose the cheapest reliable model path for each telemetry payload",
    )

    start = node(d, (1010, 200), (380, 90), "Feature Vector + Evidence Bundle", BLUE, BLUE_D, max_chars=21)
    score = node(d, (1040, 345), (320, 85), "Compute Rule Score", YELLOW, YELLOW_D)
    critical = node(d, (1040, 500), (320, 95), "Critical Signal?", RED, RED_D)
    suspicious = node(d, (700, 690), (330, 95), "Suspicious Apps or Logs?", YELLOW, YELLOW_D, max_chars=19)
    ambiguous = node(d, (360, 890), (330, 95), "Ambiguous Evidence?", PURPLE, PURPLE_D)

    low = node(d, (1050, 905), (330, 105), "Low Risk: Rules + Specialist Models", GREEN, GREEN_D, max_chars=18)
    medium = node(d, (690, 1120), (370, 110), "Medium Risk: Add Primary LLM", PURPLE, PURPLE_D, max_chars=19)
    high = node(d, (1430, 690), (390, 110), "High Risk: Primary + Reviewer LLM", RED, RED_D, max_chars=20)
    review = node(d, (240, 1120), (370, 110), "Ambiguous: LLMs + Human Review", RED, RED_D, max_chars=18)
    fusion = node(d, (1015, 1335), (370, 110), "Evidence Fusion + Final Risk", CYAN, CYAN_D, max_chars=19)

    arrow(d, edge_point(start, "b"), edge_point(score, "t"))
    arrow(d, edge_point(score, "b"), edge_point(critical, "t"))
    arrow(d, edge_point(critical, "r"), edge_point(high, "t"), elbow=(1625, 548))
    d.text((1388, 545), "Yes", fill=RED_D, font=SMALL_FONT)
    arrow(d, edge_point(critical, "l"), edge_point(suspicious, "t"), elbow=(865, 548))
    d.text((875, 585), "No", fill=MUTED, font=SMALL_FONT)
    arrow(d, edge_point(suspicious, "r"), edge_point(low, "t"), elbow=(1215, 738))
    d.text((1045, 785), "No", fill=GREEN_D, font=SMALL_FONT)
    arrow(d, edge_point(suspicious, "l"), edge_point(ambiguous, "t"), elbow=(525, 738))
    d.text((530, 790), "Yes", fill=YELLOW_D, font=SMALL_FONT)
    arrow(d, edge_point(ambiguous, "r"), edge_point(medium, "t"), elbow=(875, 938))
    d.text((705, 985), "No", fill=GREEN_D, font=SMALL_FONT)
    arrow(d, edge_point(ambiguous, "b"), edge_point(review, "t"))
    d.text((305, 1020), "Yes", fill=RED_D, font=SMALL_FONT)

    for b in [low, medium, high, review]:
        arrow(d, edge_point(b, "b"), edge_point(fusion, "t"), elbow=(center(b)[0], 1280))

    return save(img, "02-model-router-decision.png")


def chart_sequence() -> Path:
    img, d = canvas(
        "AI Analysis Sequence",
        "How one suspicious telemetry payload moves through the AI layer",
    )

    actors = [
        ("Worker", 130),
        ("Redactor", 360),
        ("Builder", 590),
        ("Router", 820),
        ("Rules", 1050),
        ("Small Models", 1280),
        ("Primary LLM", 1510),
        ("Reviewer LLM", 1740),
        ("Fusion", 1970),
        ("Store", 2200),
    ]

    for name, x in actors:
        node(d, (x - 85, 190), (170, 72), name, BLUE if name in {"Worker", "Store"} else WHITE, BLUE_D, fnt=SMALL_FONT, max_chars=11)
        d.line((x, 275, x, 1410), fill="#cbd5e1", width=3)

    events = [
        (130, 360, 340, "normalized evidence"),
        (360, 590, 460, "sanitized evidence"),
        (590, 820, 580, "evidence bundle + features"),
        (820, 1050, 700, "deterministic checks"),
        (1050, 1970, 820, "rule score + reason codes"),
        (820, 1280, 940, "classify logs/apps/posture"),
        (1280, 1970, 1060, "labels + confidence"),
        (820, 1510, 1180, "suspicious evidence"),
        (1510, 1970, 1300, "findings + evidence refs"),
        (820, 1740, 1420, "high-risk review"),
    ]
    for x1, x2, y, txt in events:
        arrow(d, (x1, y), (x2 - 12 if x2 > x1 else x2 + 12, y), color=LINE)
        d.text((min(x1, x2) + 18, y - 33), txt, fill=INK, font=TINY_FONT)
    arrow(d, (1740, 1490), (1970 - 12, 1490), color=LINE)
    d.text((1770, 1457), "objections + agreement", fill=INK, font=TINY_FONT)
    arrow(d, (1970, 1540), (2200 - 12, 1540), color=LINE)
    d.text((2000, 1507), "final assessment", fill=INK, font=TINY_FONT)

    return save(img, "03-ai-analysis-sequence.png")


def chart_lineage() -> Path:
    img, d = canvas(
        "Evidence And Storage Lineage",
        "Trace every AI finding back to raw telemetry, features, model runs, and feedback",
    )

    raw = node(d, (80, 690), (260, 95), "raw_telemetry_json", GRAY, GRAY_D)
    payload = node(d, (420, 690), (260, 95), "telemetry_payloads", BLUE, BLUE_D)
    device = node(d, (780, 430), (250, 90), "device_reports", GREEN, GREEN_D)
    apps = node(d, (780, 690), (250, 90), "app_snapshots", GREEN, GREEN_D)
    logs = node(d, (780, 950), (250, 90), "important_logs", GREEN, GREEN_D)
    current = node(d, (1110, 620), (280, 90), "app_inventory_current", CYAN, CYAN_D)
    events = node(d, (1110, 775), (280, 90), "app_inventory_events", CYAN, CYAN_D)
    features = node(d, (1490, 690), (260, 95), "risk_features", YELLOW, YELLOW_D)
    bundle = node(d, (1830, 510), (270, 90), "ai_evidence_bundles", PURPLE, PURPLE_D)
    runs = node(d, (1830, 690), (270, 90), "ai_model_runs", PURPLE, PURPLE_D)
    findings = node(d, (1830, 870), (270, 90), "ai_findings", PURPLE, PURPLE_D)
    final = node(d, (2130, 690), (220, 95), "ai_final_assessments", RED, RED_D, max_chars=16)
    feedback = node(d, (2130, 900), (220, 95), "ai_feedback_labels", RED, RED_D, max_chars=16)

    for a, b in [(raw, payload), (payload, device), (payload, apps), (payload, logs), (apps, current), (apps, events)]:
        arrow(d, edge_point(a, "r"), edge_point(b, "l"))
    for a in [device, current, events, logs]:
        arrow(d, edge_point(a, "r"), edge_point(features, "l"))
    arrow(d, edge_point(features, "r"), edge_point(bundle, "l"))
    arrow(d, edge_point(bundle, "b"), edge_point(runs, "t"))
    arrow(d, edge_point(runs, "b"), edge_point(findings, "t"))
    arrow(d, edge_point(runs, "r"), edge_point(final, "l"))
    arrow(d, edge_point(findings, "r"), edge_point(final, "l"))
    arrow(d, edge_point(final, "b"), edge_point(feedback, "t"))
    arrow(d, edge_point(feedback, "l"), edge_point(runs, "r"), elbow=(1965, 1130))

    return save(img, "04-evidence-storage-lineage.png")


def chart_deployment() -> Path:
    img, d = canvas(
        "AI Deployment Topology",
        "Keep ingestion, telemetry processing, and model analysis independently scalable",
    )

    api = node(d, (120, 310), (250, 100), "Ingestion API", BLUE, BLUE_D)
    db = node(d, (470, 210), (260, 95), "PostgreSQL Operational DB", CYAN, CYAN_D, max_chars=17)
    obj = node(d, (470, 410), (260, 95), "Raw Object Storage", CYAN, CYAN_D)
    tq = node(d, (820, 310), (260, 100), "Telemetry Queue", YELLOW, YELLOW_D)
    tw = node(d, (1160, 310), (260, 100), "Telemetry Workers", GREEN, GREEN_D)
    aiq = node(d, (1500, 310), (260, 100), "AI Analysis Queue", YELLOW, YELLOW_D)
    aiw = node(d, (1840, 310), (260, 100), "AI Worker Pool", GREEN, GREEN_D)
    router = node(d, (1840, 540), (260, 100), "Model Router", PURPLE, PURPLE_D)

    local = node(d, (1410, 790), (260, 95), "Private / Local Models", PURPLE, PURPLE_D, max_chars=16)
    prov_a = node(d, (1720, 790), (260, 95), "LLM Provider A", PURPLE, PURPLE_D)
    prov_b = node(d, (2030, 790), (260, 95), "LLM Provider B", PURPLE, PURPLE_D)
    specialist = node(d, (1720, 960), (260, 95), "Specialist Classifiers", PURPLE, PURPLE_D, max_chars=16)

    runs = node(d, (1200, 1090), (280, 95), "Model Run Store", GRAY, GRAY_D)
    fusion = node(d, (1540, 1090), (280, 95), "Evidence Fusion", RED, RED_D)
    findings = node(d, (1880, 1090), (280, 95), "AI Findings DB", RED, RED_D)
    dashboard = node(d, (1880, 1290), (280, 95), "SOC Dashboard", CYAN, CYAN_D)
    warehouse = node(d, (1540, 1290), (280, 95), "Warehouse", CYAN, CYAN_D)

    for a, b in [(api, db), (api, obj), (api, tq), (tq, tw), (tw, aiq), (aiq, aiw), (aiw, router)]:
        arrow(d, edge_point(a, "r"), edge_point(b, "l"))
    for b in [local, prov_a, prov_b, specialist]:
        arrow(d, edge_point(router, "b"), edge_point(b, "t"), elbow=(center(b)[0], 700))
    for b in [local, prov_a, prov_b, specialist]:
        arrow(d, edge_point(b, "b"), edge_point(runs, "t"), elbow=(center(b)[0], 1030))
    arrow(d, edge_point(runs, "r"), edge_point(fusion, "l"))
    arrow(d, edge_point(fusion, "r"), edge_point(findings, "l"))
    arrow(d, edge_point(findings, "b"), edge_point(dashboard, "t"))
    arrow(d, edge_point(findings, "l"), edge_point(warehouse, "t"), elbow=(1680, 1240))

    return save(img, "05-ai-deployment-topology.png")


def chart_review() -> Path:
    img, d = canvas(
        "Human Review And Learning Loop",
        "Analyst labels improve rules, prompts, models, and future routing decisions",
    )

    assessment = node(d, (920, 190), (360, 95), "Final AI Assessment", BLUE, BLUE_D)
    needs = node(d, (940, 380), (320, 95), "Needs Human Review?", YELLOW, YELLOW_D)
    auto = node(d, (1390, 570), (330, 95), "Store + Show in Dashboard", GREEN, GREEN_D, max_chars=18)
    queue = node(d, (490, 570), (330, 95), "Analyst Review Queue", RED, RED_D)
    analyst = node(d, (490, 760), (330, 95), "Security Analyst", BLUE, BLUE_D)
    label_box = node(d, (490, 950), (330, 95), "Analyst Label", YELLOW, YELLOW_D)

    tp = node(d, (120, 1160), (270, 95), "True Positive", GREEN, GREEN_D)
    fp = node(d, (440, 1160), (270, 95), "False Positive", RED, RED_D)
    benign = node(d, (760, 1160), (270, 95), "Benign", CYAN, CYAN_D)
    more = node(d, (1080, 1160), (270, 95), "Needs More Data", YELLOW, YELLOW_D)
    feedback = node(d, (1480, 1160), (300, 95), "ai_feedback_labels", PURPLE, PURPLE_D)
    evaln = node(d, (1880, 1030), (300, 95), "Evaluation Metrics", PURPLE, PURPLE_D)
    registry = node(d, (1880, 1250), (300, 95), "Model + Prompt Registry", GRAY, GRAY_D, max_chars=18)

    arrow(d, edge_point(assessment, "b"), edge_point(needs, "t"))
    arrow(d, edge_point(needs, "r"), edge_point(auto, "t"), elbow=(1555, 428))
    d.text((1285, 455), "No", fill=GREEN_D, font=SMALL_FONT)
    arrow(d, edge_point(needs, "l"), edge_point(queue, "t"), elbow=(655, 428))
    d.text((830, 455), "Yes", fill=RED_D, font=SMALL_FONT)
    arrow(d, edge_point(queue, "b"), edge_point(analyst, "t"))
    arrow(d, edge_point(analyst, "b"), edge_point(label_box, "t"))
    for b in [tp, fp, benign, more]:
        arrow(d, edge_point(label_box, "b"), edge_point(b, "t"), elbow=(center(b)[0], 1100))
        arrow(d, edge_point(b, "r"), edge_point(feedback, "l"))
    arrow(d, edge_point(feedback, "r"), edge_point(evaln, "l"))
    arrow(d, edge_point(evaln, "b"), edge_point(registry, "t"))
    arrow(d, edge_point(registry, "l"), edge_point(assessment, "r"), elbow=(1540, 1430))

    return save(img, "06-human-review-learning-loop.png")


def build_pdf(paths: list[Path]) -> None:
    pages: list[Image.Image] = []
    for path in paths:
        img = Image.open(path).convert("RGB")
        pages.append(img)
    first, rest = pages[0], pages[1:]
    first.save(PDF_PATH, "PDF", save_all=True, append_images=rest, resolution=144.0)


def main() -> None:
    paths = [
        chart_overview(),
        chart_router(),
        chart_sequence(),
        chart_lineage(),
        chart_deployment(),
        chart_review(),
    ]
    build_pdf(paths)
    print("Generated PNG charts:")
    for path in paths:
        print(path)
    print(f"Generated PDF:\n{PDF_PATH}")


if __name__ == "__main__":
    main()
