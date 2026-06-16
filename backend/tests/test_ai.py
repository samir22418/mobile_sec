from __future__ import annotations

import json
from unittest.mock import MagicMock

from sqlalchemy import select

from app.ai.analyzer import (
    AIAnalysisService,
    OpenRouterAnalyzerProvider,
    OllamaLocalAnalyzerProvider,
    ResilientLocalAnalyzerProvider,
    StubLocalAnalyzerProvider,
    build_evidence_bundle,
    provider_from_settings,
)
from app.config import Settings
from app.models import (
    AIEvidenceBundle,
    AIFinding,
    AIModelRun,
    AIRiskDecision,
    RiskAssessment,
)
from app.services.raw_store import RawPayloadStore
from app.services.worker import TelemetryWorker
from tests.conftest import important_log, sample_payload, suspicious_app


class InvalidJsonAnalyzer:
    model_name = "bad-json"
    prompt_version = "test"

    def analyze(self, evidence_bundle: dict) -> str:
        return "not-json"


class MissingEvidenceAnalyzer:
    model_name = "missing-evidence"
    prompt_version = "test"

    def analyze(self, evidence_bundle: dict) -> str:
        return '{"findings":[{"title":"unsupported"}]}'


def test_low_risk_payload_skips_llm_stub(client, app):
    response = client.post("/api/v1/telemetry", json=sample_payload())
    assert response.status_code == 202

    session = app.state.session_factory()
    try:
        assert session.scalar(select(AIModelRun)) is None
    finally:
        session.close()


def test_high_risk_payload_creates_ai_model_run(client, app):
    response = client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="ai-high", rooted=True, apps=[suspicious_app()]),
    )
    assert response.status_code == 202

    session = app.state.session_factory()
    try:
        runs = session.scalars(select(AIModelRun).where(AIModelRun.payload_id == "ai-high")).all()
        assert {run.model_role for run in runs} >= {
            "app_reputation_model",
            "posture_model",
            "primary_llm_analyst",
            "reviewer_llm",
            "evidence_fusion",
        }
        assert all(run.status == "SUCCEEDED" for run in runs)
        decision = session.scalar(select(AIRiskDecision).where(AIRiskDecision.payload_id == "ai-high"))
        assert decision is not None
        assert decision.used_ai_final
        assert session.scalar(select(AIEvidenceBundle).where(AIEvidenceBundle.payload_id == "ai-high")) is not None
        assert session.scalars(select(AIFinding).where(AIFinding.payload_id == "ai-high")).all()
    finally:
        session.close()


def test_ai_evidence_bundle_includes_counts_and_recent_history(client, app):
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="ai-history", scan_id=1, rooted=True, apps=[suspicious_app("com.example.old")]),
    )
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(
            payload_id="ai-current",
            scan_id=2,
            rooted=True,
            apps=[suspicious_app("com.example.current")],
            logs=[important_log()],
        ),
    )

    session = app.state.session_factory()
    try:
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == "ai-current"))
        bundle = build_evidence_bundle(session, "ai-current", "sample-device-001", assessment)

        assert bundle["suspicious_app_count"] == 1
        assert bundle["log_signal_count"] == 1
        assert len(bundle["recent_assessments"]) >= 2
        assert bundle["recent_assessments"][0]["payload_id"] == "ai-current"
    finally:
        session.close()


def test_ai_evidence_bundle_uses_exact_payload_app_snapshot(client, app):
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="ai-old-app", scan_id=1, apps=[suspicious_app("com.example.old")]),
    )
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="ai-current-clean", scan_id=2, rooted=True, apps=[]),
    )

    session = app.state.session_factory()
    try:
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == "ai-current-clean"))
        bundle = build_evidence_bundle(session, "ai-current-clean", "sample-device-001", assessment)

        assert bundle["suspicious_app_count"] == 0
        assert all(app["package_name"] != "com.example.old" for app in bundle["suspicious_apps"])
    finally:
        session.close()


def test_invalid_ai_json_is_stored_as_failed_run(app):
    payload_id = "bad-ai-json"
    app.state.raw_store.store(
        payload_id,
        sample_payload(payload_id=payload_id, rooted=True, apps=[suspicious_app()]),
    )
    session = app.state.session_factory()
    try:
        from app.models import TelemetryPayload

        session.add(
            TelemetryPayload(
                payload_id=payload_id,
                device_id="sample-device-001",
                scan_id=1,
                payload_created_at_epoch_ms=1,
                raw_payload_path=str(app.state.raw_store.root / f"{payload_id}.json"),
                processing_status="ACCEPTED",
            )
        )
        session.commit()
    finally:
        session.close()

    worker = TelemetryWorker(
        app.state.session_factory,
        RawPayloadStore(app.state.raw_store.root),
        ai_service=AIAnalysisService(InvalidJsonAnalyzer()),
    )
    worker.process_one(payload_id)

    session = app.state.session_factory()
    try:
        run = session.scalar(select(AIModelRun).where(AIModelRun.payload_id == payload_id))
        assert run.status == "FAILED"
        decision = session.scalar(select(AIRiskDecision).where(AIRiskDecision.payload_id == payload_id))
        assert decision.status == "FAILED"
        assert not decision.used_ai_final
    finally:
        session.close()


def test_ai_finding_without_evidence_refs_is_rejected(app):
    payload_id = "bad-ai-evidence"
    app.state.raw_store.store(
        payload_id,
        sample_payload(payload_id=payload_id, rooted=True, apps=[suspicious_app()]),
    )
    session = app.state.session_factory()
    try:
        from app.models import TelemetryPayload

        session.add(
            TelemetryPayload(
                payload_id=payload_id,
                device_id="sample-device-001",
                scan_id=1,
                payload_created_at_epoch_ms=1,
                raw_payload_path=str(app.state.raw_store.root / f"{payload_id}.json"),
                processing_status="ACCEPTED",
            )
        )
        session.commit()
    finally:
        session.close()

    worker = TelemetryWorker(
        app.state.session_factory,
        RawPayloadStore(app.state.raw_store.root),
        ai_service=AIAnalysisService(MissingEvidenceAnalyzer()),
    )
    worker.process_one(payload_id)

    session = app.state.session_factory()
    try:
        run = session.scalar(select(AIModelRun).where(AIModelRun.payload_id == payload_id))
        assert run.status == "FAILED"
    finally:
        session.close()


def test_ai_decision_endpoint_returns_baseline_and_final_score(client):
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="ai-decision", rooted=True, apps=[suspicious_app()]),
    )

    response = client.get("/api/v1/ai/decisions/ai-decision")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["deterministic_score"] <= body["decision"]["final_score"]
    assert body["decision"]["used_ai_final"] is True
    assert {run["model_role"] for run in body["runs"]} >= {"evidence_fusion"}
    assert body["evidence_bundles"]
    assert body["findings"]


def test_ai_runs_endpoint_filters_by_role(client):
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="ai-runs-filter", rooted=True, apps=[suspicious_app()], logs=[important_log()]),
    )

    response = client.get("/api/v1/ai/runs?role=logs_llm_analyst")

    assert response.status_code == 200
    assert response.json()["items"]
    assert {item["model_role"] for item in response.json()["items"]} == {"log_triage_model"}


# =============================================================================
# Provider selection and OpenRouter provider tests
# =============================================================================


def test_provider_from_settings_returns_stub_by_default():
    provider = provider_from_settings(Settings(local_llm_provider="stub"))
    assert isinstance(provider, StubLocalAnalyzerProvider)


def test_provider_from_settings_returns_resilient_ollama():
    provider = provider_from_settings(Settings(local_llm_provider="ollama"))
    assert isinstance(provider, ResilientLocalAnalyzerProvider)
    assert isinstance(provider.primary, OllamaLocalAnalyzerProvider)


def test_provider_from_settings_returns_resilient_openrouter():
    provider = provider_from_settings(Settings(local_llm_provider="openrouter", openrouter_api_key="test-key"))
    assert isinstance(provider, ResilientLocalAnalyzerProvider)
    assert isinstance(provider.primary, OpenRouterAnalyzerProvider)


def test_openrouter_provider_raises_without_api_key():
    provider = OpenRouterAnalyzerProvider(Settings(openrouter_api_key=""))
    try:
        provider.analyze("log_triage_model", {})
        assert False, "expected RuntimeError"
    except RuntimeError as error:
        assert "OPENROUTER_API_KEY" in str(error)


def test_openrouter_provider_sends_correct_request_shape(monkeypatch):
    """OpenRouterAnalyzerProvider constructs a valid chat completions request."""
    valid_output = json.dumps({
        "role": "log_triage_model",
        "confidence": 0.85,
        "findings": [
            {
                "title": "Suspicious permission access",
                "severity": "HIGH",
                "evidence_refs": ["log:1"],
                "reason": "Permission denied event matches threat pattern",
            }
        ],
    })
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"choices": [{"message": {"content": valid_output}}]}
    ).encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    captured: dict = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        return mock_response

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    settings = Settings(openrouter_api_key="sk-test", openrouter_model="openai/gpt-4o-mini")
    provider = OpenRouterAnalyzerProvider(settings)
    bundle = {
        "payload_id": "test",
        "log_signals": [{"evidence_id": "log:1", "tag": "Security", "level": "ERROR",
                          "matched_rule": "THREAT_REGEX", "message_redacted": "perm denied", "message_hash": "abc"}],
        "log_signal_count": 1,
        "evidence_refs": ["risk:rules", "log:1"],
        "risk": {"score": 55, "label": "High", "confidence": 0.7, "reasons": [], "recommended_action": "review", "needs_human_review": True},
    }
    result = provider.analyze("log_triage_model", bundle)

    decoded = json.loads(result)
    assert decoded["role"] == "log_triage_model"
    assert decoded["findings"][0]["severity"] == "HIGH"
    assert captured["body"]["model"] == "openai/gpt-4o-mini"
    assert captured["body"]["messages"][0]["role"] == "system"
    assert captured["body"]["messages"][1]["role"] == "user"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert "Bearer sk-test" in captured["auth"]


def test_openrouter_provider_model_for_role_uses_configured_model():
    settings = Settings(openrouter_model="anthropic/claude-3-haiku")
    provider = OpenRouterAnalyzerProvider(settings)
    assert provider.model_for_role("log_triage_model") == "anthropic/claude-3-haiku"
    assert provider.model_for_role("evidence_fusion") == "anthropic/claude-3-haiku"


def test_resilient_provider_falls_back_to_stub_on_ollama_failure(monkeypatch):
    """If Ollama is unreachable, ResilientLocalAnalyzerProvider returns stub output."""
    def fail(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fail)

    settings = Settings(local_llm_provider="ollama", local_llm_base_url="http://127.0.0.1:11434")
    provider = ResilientLocalAnalyzerProvider(OllamaLocalAnalyzerProvider(settings))
    bundle = {
        "payload_id": "test",
        "log_signals": [],
        "log_signal_count": 0,
        "evidence_refs": ["risk:rules"],
        "risk": {"score": 30, "label": "Low", "confidence": 0.6, "reasons": [], "recommended_action": "ok", "needs_human_review": False},
    }
    result = provider.analyze("log_triage_model", bundle)
    decoded = json.loads(result)
    assert "findings" in decoded
    assert "provider_warning" in decoded
    assert "fallback_provider" in decoded

