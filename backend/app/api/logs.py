from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.bearer import verify_analyst_token
from app.dependencies import get_session
from app.models import ImportantLog

router = APIRouter()

HIGH_SEVERITY_LEVELS = {"ERROR", "ASSERT"}


@router.get("/api/v1/logs/analysis")
def logs_analysis(
    device_id: str | None = None,
    level: str | None = None,
    matched_rule: str | None = None,
    q: str | None = None,
    limit: int = 50,
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    safe_limit = min(max(limit, 1), 200)
    query = select(ImportantLog)
    if device_id:
        query = query.where(ImportantLog.device_id == device_id)
    logs = session.scalars(query.order_by(desc(ImportantLog.observed_at_epoch_ms), desc(ImportantLog.id))).all()
    logs = filter_logs(logs, level=level, matched_rule=matched_rule, q=q)

    return build_logs_analysis(
        logs,
        safe_limit=safe_limit,
        filters={
            "device_id": device_id,
            "level": normalize_filter(level),
            "matched_rule": normalize_filter(matched_rule),
            "q": normalize_filter(q),
        },
    )


def normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def filter_logs(
    logs: Sequence[ImportantLog],
    *,
    level: str | None = None,
    matched_rule: str | None = None,
    q: str | None = None,
) -> list[ImportantLog]:
    result: list[ImportantLog] = list(logs)
    normalized_level = normalize_filter(level)
    normalized_rule = normalize_filter(matched_rule)
    normalized_query = normalize_filter(q)

    if normalized_level:
        wanted_level = normalized_level.upper()
        result = [log for log in result if log.level.upper() == wanted_level]
    if normalized_rule:
        wanted_rule = normalized_rule.upper()
        result = [log for log in result if log.matched_rule.upper() == wanted_rule]
    if normalized_query:
        needle = normalized_query.lower()
        result = [
            log
            for log in result
            if needle in log.message_redacted.lower()
            or needle in log.tag.lower()
            or needle in log.device_id.lower()
            or needle in log.payload_id.lower()
            or needle in log.message_hash.lower()
        ]
    return result


def build_logs_analysis(
    logs: list[ImportantLog],
    safe_limit: int = 50,
    filters: dict | None = None,
) -> dict:
    levels = Counter(log.level for log in logs)
    rules = Counter(log.matched_rule for log in logs)
    tags = Counter(log.tag for log in logs)
    devices = Counter(log.device_id for log in logs)
    hashes = Counter(log.message_hash for log in logs)
    high_severity_count = sum(1 for log in logs if log.level in HIGH_SEVERITY_LEVELS)

    grouped_by_hash: dict[str, list[ImportantLog]] = defaultdict(list)
    for log in logs:
        grouped_by_hash[log.message_hash].append(log)

    clusters = []
    for message_hash, members in grouped_by_hash.items():
        if len(members) < 2:
            continue
        ordered = sorted(members, key=lambda item: item.observed_at_epoch_ms)
        clusters.append(
            {
                "message_hash": message_hash,
                "count": len(members),
                "devices": sorted({member.device_id for member in members}),
                "tags": dict(Counter(member.tag for member in members).most_common(5)),
                "levels": dict(Counter(member.level for member in members).most_common()),
                "first_seen_epoch_ms": ordered[0].observed_at_epoch_ms,
                "last_seen_epoch_ms": ordered[-1].observed_at_epoch_ms,
                "sample_message": ordered[-1].message_redacted,
            }
        )
    clusters.sort(key=lambda item: (item["count"], item["last_seen_epoch_ms"]), reverse=True)

    timeline: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "high_severity": 0})
    for log in logs:
        day = datetime.fromtimestamp(log.observed_at_epoch_ms / 1000).date().isoformat()
        timeline[day]["total"] += 1
        if log.level in HIGH_SEVERITY_LEVELS:
            timeline[day]["high_severity"] += 1

    return {
        "summary": {
            "total_logs": len(logs),
            "affected_devices": len(devices),
            "high_severity_count": high_severity_count,
            "unique_message_hashes": len(hashes),
            "repeated_clusters": len(clusters),
            "threat_regex_count": rules.get("THREAT_REGEX", 0),
        },
        "by_level": dict(levels.most_common()),
        "by_rule": dict(rules.most_common()),
        "top_tags": [{"tag": tag, "count": count} for tag, count in tags.most_common(10)],
        "top_devices": [{"device_id": device, "count": count} for device, count in devices.most_common(10)],
        "timeline": [
            {
                "day": day,
                "total": values["total"],
                "high_severity": values["high_severity"],
            }
            for day, values in sorted(timeline.items())
        ],
        "clusters": clusters[:10],
        "recent_logs": [serialize_log(log) for log in logs[:safe_limit]],
        "filters": filters or {},
    }


def serialize_log(log: ImportantLog) -> dict:
    return {
        "id": log.id,
        "payload_id": log.payload_id,
        "device_id": log.device_id,
        "observed_at_epoch_ms": log.observed_at_epoch_ms,
        "tag": log.tag,
        "level": log.level,
        "matched_rule": log.matched_rule,
        "message_redacted": log.message_redacted,
        "message_hash": log.message_hash,
    }
