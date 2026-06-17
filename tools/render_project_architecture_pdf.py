from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "generated" / "project-architecture"
PDF_PATH = ROOT / "docs" / "aegis-project-architecture-and-plan.pdf"

W, H = 1800, 1125
BG = "#f4f7fb"
INK = "#172033"
MUTED = "#657381"
LINE = "#72808d"
BLUE = "#d9eaff"
BLUE_D = "#2f6fbd"
GREEN = "#ddf7e8"
GREEN_D = "#2f9d62"
YELLOW = "#fff2c6"
YELLOW_D = "#c98313"
CYAN = "#d9fbff"
CYAN_D = "#1593a3"
RED = "#ffe1e1"
RED_D = "#c43e3e"
PURPLE = "#eee5ff"
PURPLE_D = "#8247d6"
GRAY = "#edf1f5"
GRAY_D = "#56616d"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


F_TITLE = font(46, True)
F_SUB = font(22)
F_H = font(24, True)
F_BODY = font(18)
F_SMALL = font(15)
F_TINY = font(13)


def new_page(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((62, 46), title, fill=INK, font=F_TITLE)
    d.text((64, 104), subtitle, fill=MUTED, font=F_SUB)
    return img, d


def wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if sum(len(item) for item in current) + len(current) + len(word) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def box(
    d: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    subtitle: str = "",
    fill: str = BLUE,
    outline: str = BLUE_D,
    radius: int = 18,
) -> None:
    x1, y1, x2, y2 = xy
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=3)
    lines = wrap(title, max(10, (x2 - x1) // 13))
    total_h = len(lines) * 28 + (22 if subtitle else 0)
    y = y1 + ((y2 - y1) - total_h) // 2
    for line in lines:
        tw = d.textlength(line, font=F_H)
        d.text((x1 + (x2 - x1 - tw) / 2, y), line, fill=INK, font=F_H)
        y += 28
    if subtitle:
        for line in wrap(subtitle, max(14, (x2 - x1) // 10))[:2]:
            tw = d.textlength(line, font=F_SMALL)
            d.text((x1 + (x2 - x1 - tw) / 2, y), line, fill=MUTED, font=F_SMALL)
            y += 19


def arrow(
    d: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    label: str = "",
    color: str = LINE,
    width: int = 4,
) -> None:
    d.line([p1, p2], fill=color, width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    size = 14
    points = [
        p2,
        (int(p2[0] - size * math.cos(ang - 0.45)), int(p2[1] - size * math.sin(ang - 0.45))),
        (int(p2[0] - size * math.cos(ang + 0.45)), int(p2[1] - size * math.sin(ang + 0.45))),
    ]
    d.polygon(points, fill=color)
    if label:
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2 - 24
        d.rounded_rectangle((mx - 9, my - 3, mx + int(d.textlength(label, font=F_TINY)) + 9, my + 19), 6, fill=BG)
        d.text((mx, my), label, fill=INK, font=F_TINY)


def poly_arrow(
    d: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    color: str = LINE,
    width: int = 4,
) -> None:
    for start, end in zip(points, points[1:]):
        d.line([start, end], fill=color, width=width)
    if len(points) >= 2:
        p1, p2 = points[-2], points[-1]
        ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        size = 14
        d.polygon(
            [
                p2,
                (int(p2[0] - size * math.cos(ang - 0.45)), int(p2[1] - size * math.sin(ang - 0.45))),
                (int(p2[0] - size * math.cos(ang + 0.45)), int(p2[1] - size * math.sin(ang + 0.45))),
            ],
            fill=color,
        )


def note(d: ImageDraw.ImageDraw, xy: tuple[int, int], title: str, items: list[str], width: int = 430) -> None:
    x, y = xy
    d.text((x, y), title, fill=INK, font=F_H)
    y += 36
    for item in items:
        for idx, line in enumerate(wrap(item, width // 9)):
            prefix = "- " if idx == 0 else "  "
            d.text((x, y), prefix + line, fill=INK if idx == 0 else MUTED, font=F_BODY)
            y += 24


def footer(d: ImageDraw.ImageDraw, page: int) -> None:
    d.text((64, H - 52), "AEGIS mobile security project architecture", fill=MUTED, font=F_SMALL)
    d.text((W - 132, H - 52), f"Page {page}", fill=MUTED, font=F_SMALL)


def full_system() -> Image.Image:
    img, d = new_page("Full System Architecture", "Android telemetry, backend processing, local AI analysis, and analyst console")
    boxes = {
        "android": (70, 250, 310, 360),
        "agent": (400, 225, 670, 385),
        "api": (780, 245, 1030, 365),
        "storage": (1140, 165, 1430, 285),
        "worker": (1140, 350, 1430, 470),
        "ai": (1140, 535, 1430, 675),
        "ui": (1510, 300, 1740, 430),
        "chat": (1510, 545, 1740, 665),
    }
    box(d, boxes["android"], "Android Device / Emulator", "user runs scan", BLUE, BLUE_D)
    box(d, boxes["agent"], "AEGIS Agent", "posture, apps, logs, upload queue", GREEN, GREEN_D)
    box(d, boxes["api"], "FastAPI Backend", "auth, schema, idempotency", BLUE, BLUE_D)
    box(d, boxes["storage"], "Operational Storage", "SQLite now, Postgres path", CYAN, CYAN_D)
    box(d, boxes["worker"], "Worker Pipeline", "normalize, redact, score", YELLOW, YELLOW_D)
    box(d, boxes["ai"], "Local AI Lane", "Ollama, router, fusion, audit", PURPLE, PURPLE_D)
    box(d, boxes["ui"], "React Console", "devices, logs, AI Center", CYAN, CYAN_D)
    box(d, boxes["chat"], "Shieldy Chat", "OpenRouter only, separate lane", GRAY, GRAY_D)
    arrow(d, (310, 305), (400, 305), "scan")
    arrow(d, (670, 305), (780, 305), "POST /telemetry")
    arrow(d, (1030, 305), (1140, 225), "rows + raw JSON")
    arrow(d, (1030, 330), (1140, 410), "accepted payload")
    arrow(d, (1285, 470), (1285, 535), "evidence")
    arrow(d, (1430, 605), (1510, 365), "AI decisions")
    arrow(d, (1430, 225), (1510, 365), "API reads")
    arrow(d, (1625, 430), (1625, 545), "selected context")
    arrow(d, (1510, 610), (1430, 605), "audited actions")
    note(
        d,
        (80, 760),
        "Current runtime",
        [
            "FastAPI on 127.0.0.1:8080.",
            "React/Vite console on 127.0.0.1:5173.",
            "Ollama local models on 127.0.0.1:11434.",
            "OpenRouter is limited to Shieldy Chat and is not used for automated scoring.",
        ],
        690,
    )
    note(
        d,
        (900, 760),
        "Safety boundary",
        [
            "Backend validation and deterministic rules run before AI.",
            "AI outputs must be JSON with evidence references.",
            "Invalid or slow model output falls back to deterministic/stub behavior.",
        ],
        720,
    )
    footer(d, 1)
    return img


def android_agent() -> Image.Image:
    img, d = new_page("Android Agent Architecture", "How the sample app collects evidence and uploads telemetry without user code changes")
    box(d, (75, 235, 300, 345), "User", "Run Security Scan", BLUE, BLUE_D)
    box(d, (390, 210, 650, 370), "Sample App UI", "settings, status, detail view", BLUE, BLUE_D)
    box(d, (750, 145, 1030, 255), "AegisSdk", "init, config, lifecycle", GREEN, GREEN_D)
    box(d, (750, 310, 1030, 420), "DeviceScanner", "root, patch, bootloader", GREEN, GREEN_D)
    box(d, (750, 475, 1030, 585), "App Inventory", "packages and permissions", GREEN, GREEN_D)
    box(d, (750, 640, 1030, 750), "LogFilterAgent", "important logs only", GREEN, GREEN_D)
    box(d, (1125, 245, 1400, 375), "Room DB", "scan records and upload state", CYAN, CYAN_D)
    box(d, (1125, 485, 1400, 615), "WorkManager", "retry-safe upload queue", YELLOW, YELLOW_D)
    box(d, (1490, 365, 1730, 505), "TelemetryUploader", "Bearer enrollment token", PURPLE, PURPLE_D)
    arrow(d, (300, 290), (390, 290))
    arrow(d, (650, 290), (750, 200), "init")
    arrow(d, (650, 320), (750, 365), "scan")
    arrow(d, (650, 335), (750, 530), "apps")
    arrow(d, (650, 350), (750, 695), "logs")
    arrow(d, (1030, 365), (1125, 310), "payload pieces")
    arrow(d, (1030, 530), (1125, 320))
    arrow(d, (1030, 695), (1125, 320))
    arrow(d, (1260, 375), (1260, 485), "pending")
    arrow(d, (1400, 550), (1490, 435), "retry")
    arrow(d, (1730, 435), (1730, 820), "10.0.2.2:8080")
    box(d, (1455, 820, 1770, 930), "FastAPI /api/v1/telemetry", "202 accepted, idempotent", BLUE, BLUE_D)
    note(
        d,
        (80, 820),
        "Practical device onboarding",
        [
            "Analyst creates an enrollment token in backend admin UI.",
            "Android user enters backend URL, device ID, and token in app settings.",
            "No app code change is needed to add a new device in the local MVP.",
        ],
        620,
    )
    footer(d, 2)
    return img


def backend() -> Image.Image:
    img, d = new_page("Backend Architecture", "FastAPI ingestion, normalized storage, worker processing, and serving APIs")
    box(d, (65, 260, 300, 380), "Telemetry API", "Bearer token, schema v1", BLUE, BLUE_D)
    box(d, (390, 165, 650, 285), "Auth + Rate Limit", "analyst/device tokens", GRAY, GRAY_D)
    box(d, (390, 365, 650, 485), "Validation", "schema and idempotency", GRAY, GRAY_D)
    box(d, (750, 135, 1040, 255), "Raw Payload Store", "filesystem JSON", CYAN, CYAN_D)
    box(d, (750, 325, 1040, 445), "telemetry_payloads", "processing status", CYAN, CYAN_D)
    box(d, (750, 515, 1040, 635), "Worker", "normalize and redact", YELLOW, YELLOW_D)
    box(d, (1150, 200, 1430, 320), "Normalized Tables", "device, apps, logs", GREEN, GREEN_D)
    box(d, (1150, 430, 1430, 550), "Risk Engine", "deterministic baseline", YELLOW, YELLOW_D)
    box(d, (1150, 660, 1430, 790), "AI Analysis Service", "router, runs, findings", PURPLE, PURPLE_D)
    box(d, (1515, 305, 1750, 435), "Serving APIs", "devices, payloads, logs, AI", BLUE, BLUE_D)
    arrow(d, (300, 320), (390, 225))
    arrow(d, (300, 340), (390, 425))
    arrow(d, (650, 420), (750, 195), "raw")
    arrow(d, (650, 420), (750, 385), "row")
    arrow(d, (895, 445), (895, 515), "accepted")
    arrow(d, (1040, 575), (1150, 260), "normalized")
    arrow(d, (1040, 575), (1150, 490), "features")
    arrow(d, (1290, 550), (1290, 660), "suspicious cases")
    arrow(d, (1430, 260), (1515, 350))
    arrow(d, (1430, 490), (1515, 370))
    arrow(d, (1430, 725), (1515, 390))
    note(
        d,
        (80, 825),
        "Key backend tables",
        [
            "telemetry_payloads, device_reports, app_inventory_current, important_logs.",
            "risk_assessments stores deterministic baseline and displayed score.",
            "ai_evidence_bundles, ai_model_runs, ai_findings, ai_risk_decisions make the AI lane auditable.",
        ],
        800,
    )
    note(
        d,
        (980, 825),
        "Reliability choices",
        [
            "Raw JSON is stored before processing.",
            "Duplicate payload_id returns 202 without duplicate rows.",
            "AI timeout or invalid JSON does not block telemetry processing.",
        ],
        640,
    )
    footer(d, 3)
    return img


def ai_architecture() -> Image.Image:
    img, d = new_page("AI Analysis Architecture", "Real automated analysis lane, separate from the chatbot")
    y = 220
    xs = [65, 280, 500, 720, 950, 1180, 1410, 1620]
    labels = [
        ("Normalize", "device, apps, logs", GREEN, GREEN_D),
        ("Redact", "logs and PII", GREEN, GREEN_D),
        ("Evidence Bundle", "feature vector", YELLOW, YELLOW_D),
        ("Model Router", "choose path", PURPLE, PURPLE_D),
        ("Specialists", "logs, apps, posture", PURPLE, PURPLE_D),
        ("Primary LLM", "deep review", PURPLE, PURPLE_D),
        ("Reviewer LLM", "critical/ambiguous", PURPLE, PURPLE_D),
        ("Evidence Fusion", "final score", RED, RED_D),
    ]
    for i, (title, sub, fill, outline) in enumerate(labels):
        box(d, (xs[i], y, xs[i] + 170, y + 115), title, sub, fill, outline)
        if i < len(labels) - 1:
            arrow(d, (xs[i] + 170, y + 58), (xs[i + 1], y + 58))
    store_y = 520
    box(d, (250, store_y, 510, store_y + 120), "ai_evidence_bundles", "bundle hash and router path", CYAN, CYAN_D)
    box(d, (600, store_y, 860, store_y + 120), "ai_model_runs", "role, provider, latency, JSON", CYAN, CYAN_D)
    box(d, (950, store_y, 1210, store_y + 120), "ai_findings", "severity and evidence refs", CYAN, CYAN_D)
    box(d, (1300, store_y, 1560, store_y + 120), "ai_risk_decisions", "baseline vs final score", CYAN, CYAN_D)
    arrow(d, (805, y + 115), (380, store_y), "stored")
    arrow(d, (1035, y + 115), (730, store_y), "audit")
    arrow(d, (1265, y + 115), (1080, store_y), "findings")
    arrow(d, (1705, y + 115), (1430, store_y), "final")
    note(
        d,
        (80, 750),
        "Router paths",
        [
            "rules_specialists: low or simple evidence uses cheap specialist checks plus fusion.",
            "suspicious_primary: suspicious apps, logs, or medium/high baseline add primary LLM.",
            "critical_primary_reviewer: rooted, critical, or ambiguous evidence adds reviewer LLM.",
        ],
        820,
    )
    note(
        d,
        (980, 750),
        "Model contracts",
        [
            "Every model returns structured JSON only.",
            "Every finding must include evidence_refs from the bundle.",
            "Ollama can be replaced behind LocalAnalyzerProvider without changing backend APIs.",
        ],
        720,
    )
    footer(d, 4)
    return img


def ai_router() -> Image.Image:
    img, d = new_page("AI Model Router Decision Chart", "Choose the cheapest reliable model path for each telemetry payload")
    box(d, (730, 145, 1070, 235), "Feature Vector + Evidence Bundle", "", BLUE, BLUE_D)
    box(d, (760, 285, 1040, 375), "Compute Rule Score", "", YELLOW, YELLOW_D)
    box(d, (760, 425, 1040, 515), "Critical Signal?", "", RED, RED_D)
    box(d, (420, 580, 740, 675), "Suspicious Apps or Logs?", "", YELLOW, YELLOW_D)
    box(d, (1060, 580, 1420, 675), "High Risk: Primary + Reviewer LLM", "", RED, RED_D)
    box(d, (220, 765, 535, 860), "Ambiguous: LLMs + Human Review", "", RED, RED_D)
    box(d, (610, 765, 925, 860), "Medium Risk: Add Primary LLM", "", PURPLE, PURPLE_D)
    box(d, (1000, 765, 1320, 860), "Low Risk: Rules + Specialist Models", "", GREEN, GREEN_D)
    box(d, (735, 950, 1065, 1045), "Evidence Fusion + Final Risk", "", CYAN, CYAN_D)
    arrow(d, (900, 235), (900, 285))
    arrow(d, (900, 375), (900, 425))
    arrow(d, (760, 470), (580, 580), "No")
    arrow(d, (1040, 470), (1240, 580), "Yes")
    arrow(d, (580, 675), (375, 765), "Ambiguous")
    arrow(d, (580, 675), (768, 765), "Medium")
    arrow(d, (740, 628), (1160, 765), "No")
    poly_arrow(d, [(1240, 675), (1515, 675), (1515, 998), (1065, 998)])
    arrow(d, (378, 860), (815, 950))
    arrow(d, (768, 860), (880, 950))
    arrow(d, (1160, 860), (985, 950))
    note(
        d,
        (80, 210),
        "Current implementation",
        [
            "route_ai_analysis() selects specialists, primary LLM, reviewer LLM, and fusion.",
            "Critical path triggers when rooted or rule score is 80+.",
            "Ambiguous medium/high evidence can add reviewer/human review.",
        ],
        540,
    )
    footer(d, 5)
    return img


def ai_lineage() -> Image.Image:
    img, d = new_page("AI Evidence And Storage Lineage", "Trace every finding back to raw telemetry, features, model runs, and feedback")
    box(d, (70, 470, 280, 560), "raw_telemetry_json", "", GRAY, GRAY_D)
    box(d, (355, 470, 585, 560), "telemetry_payloads", "", BLUE, BLUE_D)
    box(d, (705, 290, 950, 380), "device_reports", "", GREEN, GREEN_D)
    box(d, (705, 470, 950, 560), "app_inventory_current", "", GREEN, GREEN_D)
    box(d, (705, 650, 950, 740), "important_logs", "", GREEN, GREEN_D)
    box(d, (1080, 470, 1295, 560), "risk_features", "", YELLOW, YELLOW_D)
    box(d, (1405, 250, 1655, 340), "ai_evidence_bundles", "", PURPLE, PURPLE_D)
    box(d, (1405, 430, 1655, 520), "ai_model_runs", "", PURPLE, PURPLE_D)
    box(d, (1405, 610, 1655, 700), "ai_findings", "", PURPLE, PURPLE_D)
    box(d, (1455, 790, 1710, 880), "ai_risk_decisions", "", RED, RED_D)
    arrow(d, (280, 515), (355, 515))
    arrow(d, (585, 515), (705, 335))
    arrow(d, (585, 515), (705, 515))
    arrow(d, (585, 515), (705, 695))
    arrow(d, (950, 335), (1080, 515))
    arrow(d, (950, 515), (1080, 515))
    arrow(d, (950, 695), (1080, 515))
    arrow(d, (1295, 515), (1405, 295))
    arrow(d, (1530, 340), (1530, 430))
    arrow(d, (1530, 520), (1530, 610))
    arrow(d, (1530, 700), (1580, 790))
    arrow(d, (1295, 515), (1455, 835), "fusion")
    note(
        d,
        (90, 850),
        "Why this matters",
        [
            "The UI can show which exact evidence refs affected the final score.",
            "Every model run stores role, provider, model, prompt version, latency, input hash, output JSON, and status.",
            "Feedback can later measure model quality against analyst labels.",
        ],
        1060,
    )
    footer(d, 6)
    return img


def ai_learning_loop() -> Image.Image:
    img, d = new_page("Human Review And Learning Loop", "Analyst labels improve rules, prompts, models, and routing decisions")
    box(d, (710, 165, 1030, 255), "Final AI Assessment", "", BLUE, BLUE_D)
    box(d, (710, 335, 1030, 425), "Needs Human Review?", "", YELLOW, YELLOW_D)
    box(d, (355, 515, 655, 605), "Analyst Review Queue", "", RED, RED_D)
    box(d, (355, 695, 655, 785), "Security Analyst", "", BLUE, BLUE_D)
    box(d, (355, 875, 655, 965), "Analyst Label", "", YELLOW, YELLOW_D)
    box(d, (80, 1010, 290, 1085), "True Positive", "", GREEN, GREEN_D)
    box(d, (365, 1010, 575, 1085), "False Positive", "", RED, RED_D)
    box(d, (650, 1010, 860, 1085), "Benign", "", CYAN, CYAN_D)
    box(d, (935, 1010, 1185, 1085), "Needs More Data", "", YELLOW, YELLOW_D)
    box(d, (1245, 785, 1515, 875), "ai_feedback_labels", "", PURPLE, PURPLE_D)
    box(d, (1390, 570, 1690, 660), "Evaluation Metrics", "", PURPLE, PURPLE_D)
    box(d, (1390, 365, 1690, 455), "Model + Prompt Registry", "", GRAY, GRAY_D)
    box(d, (1170, 515, 1450, 605), "Store + Show in Dashboard", "", GREEN, GREEN_D)
    arrow(d, (870, 255), (870, 335))
    arrow(d, (710, 380), (655, 560), "Yes")
    arrow(d, (1030, 380), (1170, 560), "No")
    arrow(d, (505, 605), (505, 695))
    arrow(d, (505, 785), (505, 875))
    arrow(d, (505, 965), (185, 1010))
    arrow(d, (505, 965), (470, 1010))
    arrow(d, (505, 965), (755, 1010))
    arrow(d, (505, 965), (1060, 1010))
    arrow(d, (1185, 1048), (1245, 830))
    arrow(d, (1515, 830), (1540, 660))
    arrow(d, (1540, 570), (1540, 455))
    arrow(d, (1390, 410), (940, 165), "new versions")
    footer(d, 7)
    return img


def deployment_topology() -> Image.Image:
    img, d = new_page("AI Deployment Topology", "Keep ingestion, telemetry processing, and model analysis independently scalable")
    box(d, (90, 260, 320, 370), "Ingestion API", "", BLUE, BLUE_D)
    box(d, (430, 150, 720, 250), "PostgreSQL Operational DB", "", CYAN, CYAN_D)
    box(d, (430, 390, 720, 490), "Raw Object Storage", "", CYAN, CYAN_D)
    box(d, (830, 260, 1090, 370), "Telemetry Queue", "DB-backed now", YELLOW, YELLOW_D)
    box(d, (1210, 260, 1480, 370), "Telemetry Workers", "", GREEN, GREEN_D)
    box(d, (1210, 515, 1480, 625), "AI Analysis Queue", "future Redis/RQ", YELLOW, YELLOW_D)
    box(d, (830, 515, 1090, 625), "AI Worker Pool", "", GREEN, GREEN_D)
    box(d, (500, 720, 760, 820), "Model Router", "", PURPLE, PURPLE_D)
    box(d, (95, 890, 355, 980), "Private / Local Models", "Ollama now", PURPLE, PURPLE_D)
    box(d, (470, 890, 730, 980), "Specialist Classifiers", "replaceable", PURPLE, PURPLE_D)
    box(d, (845, 890, 1105, 980), "LLM Provider B", "optional future", PURPLE, PURPLE_D)
    box(d, (1230, 790, 1490, 880), "Model Run Store", "", GRAY, GRAY_D)
    box(d, (1230, 950, 1490, 1040), "Evidence Fusion", "", RED, RED_D)
    box(d, (1550, 870, 1760, 960), "SOC Dashboard", "", CYAN, CYAN_D)
    arrow(d, (320, 315), (430, 200))
    arrow(d, (320, 330), (430, 440))
    arrow(d, (320, 315), (830, 315))
    arrow(d, (1090, 315), (1210, 315))
    arrow(d, (1345, 370), (1345, 515))
    arrow(d, (1210, 570), (1090, 570))
    arrow(d, (830, 570), (630, 720))
    arrow(d, (630, 820), (225, 890))
    arrow(d, (630, 820), (600, 890))
    arrow(d, (630, 820), (975, 890))
    arrow(d, (225, 980), (1230, 835))
    arrow(d, (600, 980), (1230, 835))
    arrow(d, (975, 980), (1230, 835))
    arrow(d, (1360, 880), (1360, 950))
    arrow(d, (1490, 995), (1550, 915))
    note(
        d,
        (80, 700),
        "MVP vs production",
        [
            "MVP can run inline or DB-backed on one machine.",
            "Production separates API, worker, AI worker, model runtime, and storage.",
            "The provider interface keeps model teams independent from API teams.",
        ],
        390,
    )
    footer(d, 8)
    return img


def project_plan() -> Image.Image:
    img, d = new_page("Project Plan And Phases", "A practical path from local MVP to reliable security product")
    phases = [
        ("1. Local Reliability", "One command starts API, React UI, Ollama. Add reset and emulator smoke scripts.", BLUE, BLUE_D),
        ("2. Data Correctness", "Replay raw payloads, harden app snapshot semantics, add schema version and agent version.", GREEN, GREEN_D),
        ("3. AI Quality", "Build labeled benchmark payloads, measure false positives, invalid JSON, latency, score drift.", PURPLE, PURPLE_D),
        ("4. Analyst Workflow", "Improve review queue, feedback labels, finding detail, and evidence drill-down in React.", CYAN, CYAN_D),
        ("5. Production Readiness", "Postgres Alembic migrations, external worker, retention, metrics, logs, backup policy.", YELLOW, YELLOW_D),
        ("6. Security Hardening", "Per-device credentials, Play Integrity backend decode, HTTPS, RBAC, audit exports.", RED, RED_D),
    ]
    x1, x2 = 120, 1680
    y0 = 205
    for i, (title, desc, fill, outline) in enumerate(phases):
        y = y0 + i * 130
        box(d, (x1, y, x1 + 330, y + 92), title, "", fill, outline)
        d.rounded_rectangle((x1 + 410, y, x2, y + 92), radius=16, fill="#ffffff", outline="#d9e1e7", width=2)
        for j, line in enumerate(wrap(desc, 100)):
            d.text((x1 + 440, y + 20 + j * 25), line, fill=INK if j == 0 else MUTED, font=F_BODY)
        if i < len(phases) - 1:
            arrow(d, (x1 + 165, y + 92), (x1 + 165, y + 130), "")
    note(
        d,
        (1010, 950),
        "AI engineer work packages",
        [
            "Provider engineer: improve Ollama/runtime adapter and model budgets.",
            "Evaluation engineer: create labeled payload/log benchmark sets.",
            "Prompt engineer: refine role prompts and JSON schemas.",
            "Data engineer: maintain lineage and feedback analytics.",
        ],
        680,
    )
    footer(d, 9)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_png in OUT_DIR.glob("*.png"):
        old_png.unlink()
    pages = [
        ("01-full-system-architecture.png", full_system()),
        ("02-android-agent-architecture.png", android_agent()),
        ("03-backend-architecture.png", backend()),
        ("04-ai-analysis-architecture.png", ai_architecture()),
        ("05-ai-model-router-decision-chart.png", ai_router()),
        ("06-ai-evidence-storage-lineage.png", ai_lineage()),
        ("07-human-review-learning-loop.png", ai_learning_loop()),
        ("08-ai-deployment-topology.png", deployment_topology()),
        ("09-project-plan-and-phases.png", project_plan()),
    ]
    rgb_pages = []
    for filename, image in pages:
        path = OUT_DIR / filename
        image.save(path)
        rgb_pages.append(image.convert("RGB"))
    rgb_pages[0].save(PDF_PATH, save_all=True, append_images=rgb_pages[1:], resolution=150)
    print(PDF_PATH)
    for filename, _ in pages:
        print(OUT_DIR / filename)


if __name__ == "__main__":
    main()
