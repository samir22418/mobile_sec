from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.bearer import verify_analyst_token
from app.dependencies import get_session
from app.models import (
    AIEvidenceBundle,
    AIFinding,
    AIModelRun,
    AIRiskDecision,
    TelemetryPayload,
)

router = APIRouter()

ROLE_ALIASES = {
    "logs_llm_analyst": ["logs_llm_analyst", "log_triage_model"],
    "telemetry_llm_analyst": ["telemetry_llm_analyst", "posture_model", "app_reputation_model"],
    "risk_llm_scorer": ["risk_llm_scorer", "evidence_fusion"],
}


@router.get("/api/v1/ai/runs")
def list_ai_runs(
    device_id: str | None = None,
    payload_id: str | None = None,
    role: str | None = None,
    limit: int = 50,
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    safe_limit = min(max(limit, 1), 200)
    query = select(AIModelRun)
    if payload_id:
        query = query.where(AIModelRun.payload_id == payload_id)
    if role:
        query = query.where(AIModelRun.model_role.in_(ROLE_ALIASES.get(role, [role])))
    if device_id:
        payload_ids = select(TelemetryPayload.payload_id).where(TelemetryPayload.device_id == device_id)
        query = query.where(AIModelRun.payload_id.in_(payload_ids))
    runs = session.scalars(query.order_by(desc(AIModelRun.created_at), desc(AIModelRun.id)).limit(safe_limit)).all()
    return {"items": [serialize_ai_run(run) for run in runs]}


@router.get("/api/v1/ai/decisions/{payload_id}")
def get_ai_decision(
    payload_id: str,
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    decision = session.scalar(select(AIRiskDecision).where(AIRiskDecision.payload_id == payload_id))
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    runs = session.scalars(
        select(AIModelRun)
        .where(AIModelRun.payload_id == payload_id)
        .order_by(desc(AIModelRun.created_at), desc(AIModelRun.id))
    ).all()
    bundles = session.scalars(
        select(AIEvidenceBundle)
        .where(AIEvidenceBundle.payload_id == payload_id)
        .order_by(desc(AIEvidenceBundle.created_at), desc(AIEvidenceBundle.id))
    ).all()
    findings = session.scalars(
        select(AIFinding)
        .where(AIFinding.payload_id == payload_id)
        .order_by(desc(AIFinding.created_at), desc(AIFinding.id))
    ).all()
    return {
        "decision": serialize_ai_decision(decision),
        "runs": [serialize_ai_run(run) for run in runs],
        "evidence_bundles": [serialize_evidence_bundle(bundle) for bundle in bundles],
        "findings": [serialize_ai_finding(finding) for finding in findings],
    }


def serialize_ai_run(run: AIModelRun) -> dict:
    try:
        output = json.loads(run.output_json)
    except json.JSONDecodeError:
        output = {"raw": run.output_json}
    return {
        "id": run.id,
        "payload_id": run.payload_id,
        "model_role": run.model_role,
        "provider": run.provider,
        "model_name": run.model_name,
        "prompt_version": run.prompt_version,
        "status": run.status,
        "latency_ms": run.latency_ms,
        "cost_estimate": run.cost_estimate,
        "output": output,
        "created_at": run.created_at.isoformat(),
    }


def serialize_ai_decision(decision: AIRiskDecision) -> dict:
    return {
        "id": decision.id,
        "payload_id": decision.payload_id,
        "device_id": decision.device_id,
        "deterministic_score": decision.deterministic_score,
        "deterministic_label": decision.deterministic_label,
        "final_score": decision.final_score,
        "final_label": decision.final_label,
        "confidence": decision.confidence,
        "reasons": json.loads(decision.reasons_json),
        "evidence_refs": json.loads(decision.evidence_refs_json),
        "recommended_action": decision.recommended_action,
        "used_ai_final": decision.used_ai_final,
        "status": decision.status,
        "created_at": decision.created_at.isoformat(),
    }


def serialize_evidence_bundle(bundle: AIEvidenceBundle) -> dict:
    return {
        "id": bundle.id,
        "payload_id": bundle.payload_id,
        "device_id": bundle.device_id,
        "bundle_stage": bundle.bundle_stage,
        "bundle_hash": bundle.bundle_hash,
        "router_path": bundle.router_path,
        "bundle": json.loads(bundle.bundle_json),
        "created_at": bundle.created_at.isoformat(),
    }


def serialize_ai_finding(finding: AIFinding) -> dict:
    return {
        "id": finding.id,
        "payload_id": finding.payload_id,
        "device_id": finding.device_id,
        "model_run_id": finding.model_run_id,
        "source_role": finding.source_role,
        "title": finding.title,
        "severity": finding.severity,
        "confidence": finding.confidence,
        "reason": finding.reason,
        "evidence_refs": json.loads(finding.evidence_refs_json),
        "status": finding.status,
        "created_at": finding.created_at.isoformat(),
    }
