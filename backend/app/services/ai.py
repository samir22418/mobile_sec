from __future__ import annotations

import hashlib
import json
import time
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import AIModelRun, AppInventoryCurrent, DeviceReport, ImportantLog, RiskAssessment


class LLMAnalyzer(Protocol):
    model_name: str
    prompt_version: str

    def analyze(self, evidence_bundle: dict) -> str:
        ...


class StubLLMAnalyzer:
    model_name = "stub-llm-analyzer"
    prompt_version = "local-stub-v1"

    def analyze(self, evidence_bundle: dict) -> str:
        findings = []
        if evidence_bundle["risk"]["score"] >= 50:
            findings.append(
                {
                    "title": "High-risk telemetry requires analyst review",
                    "severity": "HIGH",
                    "evidence_refs": evidence_bundle["evidence_refs"][:3],
                    "reason": "Deterministic risk rules found enough evidence to require review.",
                }
            )
        return json.dumps(
            {
                "model_role": "primary_llm_analyst",
                "risk_label": evidence_bundle["risk"]["label"],
                "confidence": evidence_bundle["risk"]["confidence"],
                "findings": findings,
                "recommended_action": evidence_bundle["risk"]["recommended_action"],
                "needs_human_review": evidence_bundle["risk"]["needs_human_review"],
            },
            sort_keys=True,
        )


class AIAnalysisService:
    def __init__(self, analyzer: LLMAnalyzer | None = None) -> None:
        self.analyzer = analyzer or StubLLMAnalyzer()

    def maybe_analyze(
        self,
        session: Session,
        payload_id: str,
        device_id: str,
        assessment: RiskAssessment,
    ) -> AIModelRun | None:
        if assessment.risk_score < 25:
            return None

        bundle = build_evidence_bundle(session, payload_id, device_id, assessment)
        bundle_json = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
        bundle_hash = hashlib.sha256(bundle_json.encode("utf-8")).hexdigest()

        started = time.perf_counter()
        status = "SUCCEEDED"
        try:
            output = self.analyzer.analyze(bundle)
            validate_model_output(output)
        except Exception as error:
            status = "FAILED"
            output = json.dumps({"error": str(error)}, sort_keys=True)

        latency_ms = int((time.perf_counter() - started) * 1000)
        run = AIModelRun(
            payload_id=payload_id,
            model_role="primary_llm_analyst",
            model_name=self.analyzer.model_name,
            prompt_version=self.analyzer.prompt_version,
            input_bundle_hash=bundle_hash,
            output_json=output,
            status=status,
            latency_ms=latency_ms,
            cost_estimate=0.0,
        )
        session.add(run)
        return run


def build_evidence_bundle(
    session: Session,
    payload_id: str,
    device_id: str,
    assessment: RiskAssessment,
) -> dict:
    device_report = session.query(DeviceReport).filter_by(payload_id=payload_id).one_or_none()
    apps = session.query(AppInventoryCurrent).filter_by(device_id=device_id).all()
    logs = session.query(ImportantLog).filter_by(payload_id=payload_id).all()

    evidence_refs = ["risk:rules"]
    posture = {}
    if device_report is not None:
        posture = {
            "is_rooted": device_report.is_rooted,
            "root_signal_count": device_report.root_signal_count,
            "integrity_verdict": device_report.integrity_verdict,
            "security_patch_age_days": device_report.security_patch_age_days,
            "bootloader_state": device_report.bootloader_state,
        }
        evidence_refs.append("posture:device_report")

    suspicious_apps = []
    for app in apps:
        if app.install_source in {"SIDELOADED", "UNKNOWN"}:
            suspicious_apps.append(
                {
                    "evidence_id": f"app:{app.package_name}",
                    "package_name": app.package_name,
                    "install_source": app.install_source,
                    "requested_permissions": json.loads(app.requested_permissions_json),
                }
            )
            evidence_refs.append(f"app:{app.package_name}")

    log_signals = []
    for log in logs[:10]:
        log_signals.append(
            {
                "evidence_id": f"log:{log.id}",
                "tag": log.tag,
                "level": log.level,
                "matched_rule": log.matched_rule,
                "message_redacted": log.message_redacted,
            }
        )
        evidence_refs.append(f"log:{log.id}")

    return {
        "payload_id": payload_id,
        "device_id": device_id,
        "posture": posture,
        "suspicious_apps": suspicious_apps,
        "log_signals": log_signals,
        "risk": {
            "score": assessment.risk_score,
            "label": assessment.risk_label,
            "confidence": assessment.confidence,
            "reasons": json.loads(assessment.reasons_json),
            "recommended_action": assessment.recommended_action,
            "needs_human_review": assessment.needs_human_review,
        },
        "evidence_refs": evidence_refs,
    }


def validate_model_output(output: str) -> None:
    decoded = json.loads(output)
    if not isinstance(decoded, dict):
        raise ValueError("model output is not a JSON object")
    findings = decoded.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")
    for finding in findings:
        if not finding.get("evidence_refs"):
            raise ValueError("AI finding is missing evidence references")

