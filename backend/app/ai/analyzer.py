from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import Settings, load_settings
from app.models import (
    AIEvidenceBundle,
    AIFinding,
    AIModelRun,
    AIRiskDecision,
    AppInventoryCurrent,
    DeviceReport,
    ImportantLog,
    RiskAssessment,
    TelemetryPayload,
)
from app.risk.scorer import recommended_action, risk_label

LOGS_ANALYST = "logs_llm_analyst"
TELEMETRY_ANALYST = "telemetry_llm_analyst"
RISK_SCORER = "risk_llm_scorer"
LOG_TRIAGE_MODEL = "log_triage_model"
APP_REPUTATION_MODEL = "app_reputation_model"
POSTURE_MODEL = "posture_model"
PRIMARY_LLM_ANALYST = "primary_llm_analyst"
REVIEWER_LLM = "reviewer_llm"
EVIDENCE_FUSION = "evidence_fusion"
STRUCTURED_AI_ROLES = {
    LOG_TRIAGE_MODEL,
    APP_REPUTATION_MODEL,
    POSTURE_MODEL,
    PRIMARY_LLM_ANALYST,
    REVIEWER_LLM,
    EVIDENCE_FUSION,
}


class LLMAnalyzer(Protocol):
    model_name: str
    prompt_version: str

    def analyze(self, evidence_bundle: dict) -> str:
        ...


class LocalAnalyzerProvider(Protocol):
    provider_name: str
    prompt_version: str

    def model_for_role(self, role: str) -> str:
        ...

    def analyze(self, role: str, evidence_bundle: dict) -> str:
        ...


class ResilientLocalAnalyzerProvider:
    def __init__(self, primary: LocalAnalyzerProvider, fallback: LocalAnalyzerProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or StubLocalAnalyzerProvider()
        self.prompt_version = primary.prompt_version
        self.provider_name = f"{primary.provider_name}_with_stub_fallback"

    def model_for_role(self, role: str) -> str:
        return self.primary.model_for_role(role)

    def analyze(self, role: str, evidence_bundle: dict) -> str:
        try:
            output = self.primary.analyze(role, evidence_bundle)
            ensure_role_output_shape(role, output)
            return output
        except Exception as error:
            fallback_output = json.loads(self.fallback.analyze(role, evidence_bundle))
            fallback_output["provider_warning"] = f"{self.primary.provider_name} unavailable or invalid for {role}: {error}"
            fallback_output["fallback_provider"] = self.fallback.provider_name
            return json.dumps(fallback_output, sort_keys=True)


@dataclass
class RoleResult:
    run: AIModelRun
    output: dict


@dataclass(frozen=True)
class RouterDecision:
    path: str
    roles: tuple[str, ...]
    needs_reviewer: bool
    reasons: tuple[str, ...]


class StubLLMAnalyzer:
    model_name = "stub-llm-analyzer"
    prompt_version = "local-stub-v1"

    def analyze(self, evidence_bundle: dict) -> str:
        return StubLocalAnalyzerProvider().analyze("primary_llm_analyst", evidence_bundle)


class StubLocalAnalyzerProvider:
    provider_name = "local_stub"
    prompt_version = "local-security-v1"

    def __init__(
        self,
        logs_model: str = "stub-logs-model",
        telemetry_model: str = "stub-telemetry-model",
        risk_model: str = "stub-risk-model",
    ) -> None:
        self.models = {
            LOGS_ANALYST: logs_model,
            TELEMETRY_ANALYST: telemetry_model,
            RISK_SCORER: risk_model,
            LOG_TRIAGE_MODEL: logs_model,
            APP_REPUTATION_MODEL: telemetry_model,
            POSTURE_MODEL: telemetry_model,
            PRIMARY_LLM_ANALYST: risk_model,
            REVIEWER_LLM: risk_model,
            EVIDENCE_FUSION: risk_model,
            "primary_llm_analyst": risk_model,
        }

    def model_for_role(self, role: str) -> str:
        return self.models.get(role, "stub-security-model")

    def analyze(self, role: str, evidence_bundle: dict) -> str:
        if role in {LOGS_ANALYST, LOG_TRIAGE_MODEL}:
            findings = []
            if evidence_bundle.get("log_signal_count", 0):
                findings.append(
                    {
                        "title": "Important security logs need review",
                        "severity": "MEDIUM",
                        "evidence_refs": evidence_bundle.get("evidence_refs", ["risk:rules"])[:5],
                        "reason": "The payload contains redacted log signals selected by the Android collector.",
                    }
                )
            return json.dumps({"role": role, "confidence": 0.72, "findings": findings}, sort_keys=True)

        if role in {TELEMETRY_ANALYST, POSTURE_MODEL}:
            posture = evidence_bundle.get("posture", {})
            findings = []
            if posture.get("is_rooted") or posture.get("integrity_verdict") not in {None, "MEETS_DEVICE_INTEGRITY"}:
                findings.append(
                    {
                        "title": "Device posture contains trust warnings",
                        "severity": "HIGH" if posture.get("is_rooted") else "MEDIUM",
                        "evidence_refs": evidence_bundle.get("evidence_refs", ["posture:device_report"])[:5],
                        "reason": "Root, integrity, patch, or bootloader posture may reduce device trust.",
                    }
                )
            return json.dumps({"role": role, "confidence": 0.76, "findings": findings}, sort_keys=True)

        if role == APP_REPUTATION_MODEL:
            findings = []
            suspicious_count = int(evidence_bundle.get("suspicious_app_count", 0))
            if suspicious_count:
                findings.append(
                    {
                        "title": "Sideloaded sensitive app inventory requires review",
                        "severity": "HIGH" if suspicious_count >= 3 else "MEDIUM",
                        "evidence_refs": evidence_bundle.get("evidence_refs", ["risk:rules"])[:8],
                        "reason": f"{suspicious_count} sideloaded or unknown-source app(s) requested sensitive permissions.",
                    }
                )
            return json.dumps({"role": role, "confidence": 0.74, "findings": findings}, sort_keys=True)

        if role in {PRIMARY_LLM_ANALYST, REVIEWER_LLM}:
            risk = evidence_bundle.get("risk", {})
            findings = []
            if int(risk.get("score", 0)) >= 50:
                findings.append(
                    {
                        "title": "Suspicious telemetry warrants analyst attention",
                        "severity": str(risk.get("label", "High")).upper(),
                        "evidence_refs": evidence_bundle.get("evidence_refs", ["risk:rules"])[:8],
                        "reason": "Rules, posture, logs, and app evidence indicate elevated device risk.",
                    }
                )
            return json.dumps(
                {
                    "role": role,
                    "confidence": 0.8 if role == PRIMARY_LLM_ANALYST else 0.78,
                    "agreement": "AGREE" if role == REVIEWER_LLM else None,
                    "objections": [] if role == REVIEWER_LLM else None,
                    "findings": findings,
                },
                sort_keys=True,
            )

        risk = evidence_bundle.get("risk", {})
        score = int(risk.get("score", 0))
        evidence_refs = evidence_bundle.get("evidence_refs", ["risk:rules"])
        if evidence_bundle.get("log_signal_count", 0) >= 10:
            score += 5
        if evidence_bundle.get("suspicious_app_count", 0):
            score += 5
        final_score = min(max(score, 0), 100)
        label = risk_label(final_score)
        output = {
            "role": role,
            "final_score": final_score,
            "label": label,
            "confidence": max(float(risk.get("confidence", 0.7)), 0.75),
            "reasons": list(risk.get("reasons", [])),
            "evidence_refs": evidence_refs[:8],
            "recommended_action": recommended_action(label, bool(evidence_bundle.get("posture", {}).get("is_rooted"))),
            "needs_human_review": final_score >= 50,
            "findings": [
                {
                    "title": "AI final risk score produced",
                    "severity": label.upper(),
                    "evidence_refs": evidence_refs[:5],
                    "reason": "Local scorer combined deterministic rules with local analyst findings.",
                }
            ],
        }
        return json.dumps(output, sort_keys=True)


class OllamaLocalAnalyzerProvider(StubLocalAnalyzerProvider):
    provider_name = "ollama"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings.logs_model, settings.telemetry_model, settings.risk_model)
        self.base_url = settings.local_llm_base_url.rstrip("/")
        self.timeout_seconds = settings.local_llm_timeout_seconds

    def analyze(self, role: str, evidence_bundle: dict) -> str:
        prompt = build_role_prompt(role, evidence_bundle)
        body = json.dumps(
            {
                "model": self.model_for_role(role),
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 450,
                },
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Ollama request failed: {error}") from error
        content = payload.get("response")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama response did not include JSON content")
        return content


class OpenRouterAnalyzerProvider(StubLocalAnalyzerProvider):
    """Use OpenRouter (OpenAI-compatible) API for AI analysis roles.

    Enabled by setting AEGIS_LOCAL_LLM_PROVIDER=openrouter and OPENROUTER_API_KEY.
    All roles use the same model (OPENROUTER_MODEL), which can be any model
    available on OpenRouter such as openai/gpt-4o-mini or a free deepseek model.
    """

    provider_name = "openrouter"
    prompt_version = "openrouter-security-v1"

    def __init__(self, settings: Settings) -> None:
        model = settings.openrouter_model or "openai/gpt-4o-mini"
        super().__init__(logs_model=model, telemetry_model=model, risk_model=model)
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.timeout_seconds = settings.openrouter_timeout_seconds

    def analyze(self, role: str, evidence_bundle: dict) -> str:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set — cannot use openrouter provider")
        prompt = build_role_prompt(role, evidence_bundle)
        body = json.dumps(
            {
                "model": self.model_for_role(role),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are AEGIS, a mobile security analysis model. "
                            "Return only one compact JSON object. Do not include markdown, code fences, or explanations."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:8080",
                "X-Title": "AEGIS AI Analyzer",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise RuntimeError(f"OpenRouter analysis request failed: {error}") from error
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter analysis response did not include content")
        return content


def provider_from_settings(settings: Settings | None = None) -> LocalAnalyzerProvider:
    settings = settings or load_settings()
    if settings.local_llm_provider == "ollama":
        return ResilientLocalAnalyzerProvider(OllamaLocalAnalyzerProvider(settings))
    if settings.local_llm_provider == "openrouter":
        return ResilientLocalAnalyzerProvider(OpenRouterAnalyzerProvider(settings))
    return StubLocalAnalyzerProvider(settings.logs_model, settings.telemetry_model, settings.risk_model)


class AIAnalysisService:
    def __init__(
        self,
        analyzer: LLMAnalyzer | None = None,
        provider: LocalAnalyzerProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.legacy_analyzer = analyzer
        self.provider = provider or provider_from_settings(self.settings)

    def maybe_analyze(
        self,
        session: Session,
        payload_id: str,
        device_id: str,
        assessment: RiskAssessment,
    ) -> AIModelRun | None:
        if assessment.risk_score < 25:
            create_risk_decision(session, payload_id, device_id, assessment, None, status="SKIPPED")
            return None

        if self.legacy_analyzer is not None:
            return self._run_legacy_analyzer(session, payload_id, device_id, assessment)

        base_bundle = build_evidence_bundle(session, payload_id, device_id, assessment)
        router_decision = route_ai_analysis(base_bundle)
        routed_bundle = {
            **base_bundle,
            "router_decision": {
                "path": router_decision.path,
                "roles": list(router_decision.roles),
                "needs_reviewer": router_decision.needs_reviewer,
                "reasons": list(router_decision.reasons),
            },
        }
        store_evidence_bundle(session, payload_id, device_id, "feature_bundle", router_decision.path, routed_bundle)

        role_outputs: dict[str, dict] = {}
        last_run: AIModelRun | None = None
        for role in router_decision.roles:
            role_bundle = build_role_evidence_bundle(role, routed_bundle, role_outputs)
            result = self._run_role(
                session,
                payload_id,
                role,
                role_bundle,
                expect_risk=role == EVIDENCE_FUSION,
            )
            last_run = result.run
            role_outputs[role] = result.output
            session.flush()
            store_findings(session, payload_id, device_id, role, result)

        fusion_output = role_outputs.get(EVIDENCE_FUSION)
        status = last_run.status if last_run is not None else "SKIPPED"
        create_risk_decision(session, payload_id, device_id, assessment, fusion_output, status=status)
        if last_run is not None and last_run.status == "SUCCEEDED" and fusion_output:
            apply_ai_final_risk(assessment, fusion_output)
        return last_run

    def _run_role(
        self,
        session: Session,
        payload_id: str,
        role: str,
        bundle: dict,
        expect_risk: bool = False,
    ) -> RoleResult:
        return run_model_call(
            session=session,
            payload_id=payload_id,
            role=role,
            provider_name=self.provider.provider_name,
            model_name=self.provider.model_for_role(role),
            prompt_version=self.provider.prompt_version,
            bundle=bundle,
            call=lambda: self.provider.analyze(role, bundle),
            expect_risk=expect_risk,
        )

    def _run_legacy_analyzer(
        self,
        session: Session,
        payload_id: str,
        device_id: str,
        assessment: RiskAssessment,
    ) -> AIModelRun:
        assert self.legacy_analyzer is not None
        bundle = build_evidence_bundle(session, payload_id, device_id, assessment)
        result = run_model_call(
            session=session,
            payload_id=payload_id,
            role="primary_llm_analyst",
            provider_name="legacy",
            model_name=self.legacy_analyzer.model_name,
            prompt_version=self.legacy_analyzer.prompt_version,
            bundle=bundle,
            call=lambda: self.legacy_analyzer.analyze(bundle),
            expect_risk=False,
        )
        create_risk_decision(session, payload_id, device_id, assessment, None, status=result.run.status)
        return result.run


def run_model_call(
    *,
    session: Session,
    payload_id: str,
    role: str,
    provider_name: str,
    model_name: str,
    prompt_version: str,
    bundle: dict,
    call,
    expect_risk: bool = False,
) -> RoleResult:
    bundle_json = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    bundle_hash = hashlib.sha256(bundle_json.encode("utf-8")).hexdigest()
    started = time.perf_counter()
    status = "SUCCEEDED"
    try:
        output = call()
        decoded = validate_risk_output(output) if expect_risk else validate_model_output(output)
    except Exception as error:
        status = "FAILED"
        decoded = {"error": str(error), "findings": []}
        output = json.dumps(decoded, sort_keys=True)

    run = AIModelRun(
        payload_id=payload_id,
        model_role=role,
        provider=provider_name,
        model_name=model_name,
        prompt_version=prompt_version,
        input_bundle_hash=bundle_hash,
        output_json=output,
        status=status,
        latency_ms=int((time.perf_counter() - started) * 1000),
        cost_estimate=0.0,
    )
    session.add(run)
    return RoleResult(run=run, output=decoded)


def create_risk_decision(
    session: Session,
    payload_id: str,
    device_id: str,
    assessment: RiskAssessment,
    output: dict | None,
    status: str,
) -> AIRiskDecision:
    existing = session.query(AIRiskDecision).filter_by(payload_id=payload_id).one_or_none()
    if existing is not None:
        return existing
    valid_output = output if status == "SUCCEEDED" else None
    final_score = int(valid_output["final_score"]) if valid_output else assessment.risk_score
    final_label = str(valid_output["label"]) if valid_output else assessment.risk_label
    reasons = valid_output.get("reasons", json.loads(assessment.reasons_json)) if valid_output else json.loads(assessment.reasons_json)
    evidence_refs = valid_output.get("evidence_refs", ["risk:rules"]) if valid_output else ["risk:rules"]
    decision = AIRiskDecision(
        payload_id=payload_id,
        device_id=device_id,
        deterministic_score=assessment.risk_score,
        deterministic_label=assessment.risk_label,
        final_score=final_score,
        final_label=final_label,
        confidence=float(valid_output.get("confidence", assessment.confidence)) if valid_output else assessment.confidence,
        reasons_json=json.dumps(reasons, sort_keys=True),
        evidence_refs_json=json.dumps(evidence_refs, sort_keys=True),
        recommended_action=str(valid_output.get("recommended_action", assessment.recommended_action)) if valid_output else assessment.recommended_action,
        used_ai_final=valid_output is not None,
        status=status,
    )
    session.add(decision)
    return decision


def apply_ai_final_risk(assessment: RiskAssessment, output: dict) -> None:
    assessment.risk_score = int(output["final_score"])
    assessment.risk_label = str(output["label"])
    assessment.confidence = float(output["confidence"])
    assessment.reasons_json = json.dumps(output["reasons"], sort_keys=True)
    assessment.recommended_action = str(output["recommended_action"])
    assessment.needs_human_review = bool(output.get("needs_human_review", assessment.risk_score >= 50))


def build_evidence_bundle(
    session: Session,
    payload_id: str,
    device_id: str,
    assessment: RiskAssessment,
) -> dict:
    raw_payload = load_raw_payload(session, payload_id)
    device_report = session.query(DeviceReport).filter_by(payload_id=payload_id).one_or_none()
    apps = session.query(AppInventoryCurrent).filter_by(device_id=device_id).all()
    logs = session.query(ImportantLog).filter_by(payload_id=payload_id).order_by(desc(ImportantLog.observed_at_epoch_ms)).all()

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
    raw_apps = (raw_payload.get("app_snapshot") or {}).get("apps") if raw_payload else None
    app_evidence = raw_apps if isinstance(raw_apps, list) else apps
    for app in app_evidence:
        install_source = app.get("install_source") if isinstance(app, dict) else app.install_source
        if install_source in {"SIDELOADED", "UNKNOWN"}:
            package_name = app.get("package_name") if isinstance(app, dict) else app.package_name
            permissions = app.get("requested_permissions", []) if isinstance(app, dict) else json.loads(app.requested_permissions_json)
            suspicious_apps.append(
                {
                    "evidence_id": f"app:{package_name}",
                    "package_name": package_name,
                    "install_source": install_source,
                    "requested_permissions": permissions,
                }
            )
            evidence_refs.append(f"app:{package_name}")

    log_signals = []
    for log in logs[:20]:
        log_signals.append(
            {
                "evidence_id": f"log:{log.id}",
                "tag": log.tag,
                "level": log.level,
                "matched_rule": log.matched_rule,
                "message_redacted": log.message_redacted,
                "message_hash": log.message_hash,
            }
        )
        evidence_refs.append(f"log:{log.id}")

    recent_assessments = [
        {
            "payload_id": previous.payload_id,
            "risk_score": previous.risk_score,
            "risk_label": previous.risk_label,
            "created_at": previous.created_at.isoformat(),
        }
        for previous in session.query(RiskAssessment)
        .filter(RiskAssessment.device_id == device_id)
        .order_by(desc(RiskAssessment.created_at), desc(RiskAssessment.id))
        .limit(5)
        .all()
    ]

    return {
        "payload_id": payload_id,
        "device_id": device_id,
        "posture": posture,
        "suspicious_apps": suspicious_apps,
        "suspicious_app_count": len(suspicious_apps),
        "log_signals": log_signals,
        "log_signal_count": len(logs),
        "risk": {
            "score": assessment.risk_score,
            "label": assessment.risk_label,
            "confidence": assessment.confidence,
            "reasons": json.loads(assessment.reasons_json),
            "recommended_action": assessment.recommended_action,
            "needs_human_review": assessment.needs_human_review,
        },
        "recent_assessments": recent_assessments,
        "evidence_refs": evidence_refs,
    }


def build_logs_evidence_bundle(base: dict) -> dict:
    return {
        "payload_id": base["payload_id"],
        "device_id": base["device_id"],
        "log_signals": base["log_signals"],
        "log_signal_count": base["log_signal_count"],
        "risk": base["risk"],
        "evidence_refs": ["risk:rules", *[log["evidence_id"] for log in base["log_signals"]]],
    }


def build_telemetry_evidence_bundle(base: dict) -> dict:
    return {
        "payload_id": base["payload_id"],
        "device_id": base["device_id"],
        "posture": base["posture"],
        "suspicious_apps": base["suspicious_apps"][:20],
        "suspicious_app_count": base["suspicious_app_count"],
        "recent_assessments": base["recent_assessments"],
        "risk": base["risk"],
        "evidence_refs": [ref for ref in base["evidence_refs"] if not ref.startswith("log:")],
    }


def build_risk_evidence_bundle(base: dict, logs_output: dict, telemetry_output: dict) -> dict:
    return {
        **base,
        "logs_ai": logs_output,
        "telemetry_ai": telemetry_output,
    }


def route_ai_analysis(bundle: dict) -> RouterDecision:
    risk = bundle.get("risk", {})
    posture = bundle.get("posture", {})
    score = int(risk.get("score", 0))
    log_count = int(bundle.get("log_signal_count", 0))
    app_count = int(bundle.get("suspicious_app_count", 0))
    critical_signal = bool(posture.get("is_rooted")) or score >= 80
    suspicious_signal = log_count > 0 or app_count > 0 or score >= 50
    ambiguous_signal = 45 <= score < 65 or (log_count > 0 and score < 55)

    reasons = []
    roles: list[str] = []
    if log_count:
        roles.append(LOG_TRIAGE_MODEL)
        reasons.append(f"{log_count} redacted important log(s)")
    if app_count:
        roles.append(APP_REPUTATION_MODEL)
        reasons.append(f"{app_count} suspicious app(s)")
    if posture or score >= 25:
        roles.append(POSTURE_MODEL)
        reasons.append("device posture and integrity evidence")

    if critical_signal:
        path = "critical_primary_reviewer"
        roles.extend([PRIMARY_LLM_ANALYST, REVIEWER_LLM, EVIDENCE_FUSION])
        reasons.append("critical signal or score >= 80")
        return RouterDecision(path, tuple(dict.fromkeys(roles)), True, tuple(reasons))

    if suspicious_signal:
        path = "suspicious_primary"
        roles.append(PRIMARY_LLM_ANALYST)
        if ambiguous_signal:
            roles.append(REVIEWER_LLM)
            reasons.append("ambiguous medium/high evidence")
        roles.append(EVIDENCE_FUSION)
        return RouterDecision(path, tuple(dict.fromkeys(roles)), ambiguous_signal, tuple(reasons))

    roles.append(EVIDENCE_FUSION)
    return RouterDecision("rules_specialists", tuple(dict.fromkeys(roles)), False, tuple(reasons or ["baseline rules review"]))


def build_role_evidence_bundle(role: str, base: dict, role_outputs: dict[str, dict]) -> dict:
    if role == LOG_TRIAGE_MODEL:
        return build_logs_evidence_bundle(base)
    if role == APP_REPUTATION_MODEL:
        return {
            "payload_id": base["payload_id"],
            "device_id": base["device_id"],
            "suspicious_apps": base["suspicious_apps"][:30],
            "suspicious_app_count": base["suspicious_app_count"],
            "risk": base["risk"],
            "evidence_refs": [
                ref for ref in base["evidence_refs"] if ref == "risk:rules" or ref.startswith("app:")
            ],
        }
    if role == POSTURE_MODEL:
        return build_telemetry_evidence_bundle(base)
    if role == PRIMARY_LLM_ANALYST:
        return {
            **base,
            "specialist_outputs": {
                key: value
                for key, value in role_outputs.items()
                if key in {LOG_TRIAGE_MODEL, APP_REPUTATION_MODEL, POSTURE_MODEL}
            },
        }
    if role == REVIEWER_LLM:
        return {
            **base,
            "primary_output": role_outputs.get(PRIMARY_LLM_ANALYST, {}),
            "specialist_outputs": {
                key: value
                for key, value in role_outputs.items()
                if key in {LOG_TRIAGE_MODEL, APP_REPUTATION_MODEL, POSTURE_MODEL}
            },
        }
    return {
        **base,
        "model_outputs": role_outputs,
    }


def store_evidence_bundle(
    session: Session,
    payload_id: str,
    device_id: str,
    stage: str,
    router_path: str,
    bundle: dict,
) -> AIEvidenceBundle:
    bundle_json = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    bundle_hash = hashlib.sha256(bundle_json.encode("utf-8")).hexdigest()
    existing = session.query(AIEvidenceBundle).filter_by(payload_id=payload_id, bundle_stage=stage).one_or_none()
    if existing is not None:
        return existing
    record = AIEvidenceBundle(
        payload_id=payload_id,
        device_id=device_id,
        bundle_stage=stage,
        bundle_hash=bundle_hash,
        router_path=router_path,
        bundle_json=bundle_json,
    )
    session.add(record)
    return record


def store_findings(
    session: Session,
    payload_id: str,
    device_id: str,
    role: str,
    result: RoleResult,
) -> None:
    findings = result.output.get("findings", [])
    if not isinstance(findings, list):
        return
    confidence = float(result.output.get("confidence", 0.0) or 0.0)
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        evidence_refs = normalize_evidence_refs(finding.get("evidence_refs"))
        if not evidence_refs:
            continue
        session.add(
            AIFinding(
                payload_id=payload_id,
                device_id=device_id,
                model_run_id=result.run.id,
                source_role=role,
                title=str(finding.get("title") or "AI finding"),
                severity=str(finding.get("severity") or "MEDIUM").upper(),
                confidence=confidence,
                reason=str(finding.get("reason") or ""),
                evidence_refs_json=json.dumps(evidence_refs, sort_keys=True),
            )
        )


def load_raw_payload(session: Session, payload_id: str) -> dict | None:
    record = session.query(TelemetryPayload).filter_by(payload_id=payload_id).one_or_none()
    if record is None:
        return None
    try:
        with open(record.raw_payload_path, encoding="utf-8") as handle:
            raw_payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return raw_payload if isinstance(raw_payload, dict) else None


def validate_model_output(output: str) -> dict:
    decoded = json.loads(output)
    if not isinstance(decoded, dict):
        raise ValueError("model output is not a JSON object")
    findings = decoded.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")
    for finding in findings:
        if not isinstance(finding, dict) or not normalize_evidence_refs(finding.get("evidence_refs")):
            raise ValueError("AI finding is missing evidence references")
        finding["evidence_refs"] = normalize_evidence_refs(finding.get("evidence_refs"))
    return decoded


def validate_risk_output(output: str) -> dict:
    decoded = validate_model_output(output)
    for field in ["final_score", "label", "confidence", "reasons", "evidence_refs", "recommended_action"]:
        if field not in decoded:
            raise ValueError(f"risk output missing {field}")
    final_score = int(decoded["final_score"])
    if not 0 <= final_score <= 100:
        raise ValueError("final_score must be between 0 and 100")
    if not decoded["evidence_refs"]:
        raise ValueError("risk output missing evidence references")
    decoded["evidence_refs"] = normalize_evidence_refs(decoded["evidence_refs"])
    if not decoded["evidence_refs"]:
        raise ValueError("risk output missing evidence references")
    if not isinstance(decoded["reasons"], list):
        raise ValueError("reasons must be a list")
    decoded["final_score"] = final_score
    decoded["confidence"] = float(decoded["confidence"])
    return decoded


def normalize_evidence_refs(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.replace(",", " ").split() if part.strip()]
    return []


def ensure_role_output_shape(role: str, output: str) -> None:
    if role == RISK_SCORER:
        validate_risk_output(output)
    else:
        decoded = validate_model_output(output)
        if "role" not in decoded:
            raise ValueError("model output missing role")
        if "confidence" not in decoded:
            raise ValueError("model output missing confidence")


def build_role_prompt(role: str, bundle: dict) -> str:
    evidence_json = json.dumps(bundle, sort_keys=True)
    if role in {LOGS_ANALYST, LOG_TRIAGE_MODEL}:
        schema = (
            f'{{"role":"{role}","confidence":0.0,'
            '"findings":[{"title":"","severity":"LOW|MEDIUM|HIGH|CRITICAL",'
            '"evidence_refs":["risk:rules"],"reason":""}]}'
        )
    elif role in {TELEMETRY_ANALYST, POSTURE_MODEL, APP_REPUTATION_MODEL, PRIMARY_LLM_ANALYST, REVIEWER_LLM}:
        schema = (
            f'{{"role":"{role}","confidence":0.0,'
            '"findings":[{"title":"","severity":"LOW|MEDIUM|HIGH|CRITICAL",'
            '"evidence_refs":["posture:device_report"],"reason":""}]}'
        )
    else:
        schema = (
            '{"role":"risk_llm_scorer","final_score":0,"label":"Low|Medium|High|Critical",'
            '"confidence":0.0,"reasons":[],"evidence_refs":["risk:rules"],'
            '"recommended_action":"","needs_human_review":false,'
            '"findings":[{"title":"","severity":"LOW|MEDIUM|HIGH|CRITICAL",'
            '"evidence_refs":["risk:rules"],"reason":""}]}'
        )
    return (
        "You are an AEGIS local mobile security model. "
        "Return only one compact JSON object. Do not include markdown. "
        "Use only evidence_refs that appear in the evidence bundle. "
        f"Required JSON schema example: {schema}. "
        f"Evidence bundle: {evidence_json}"
    )
