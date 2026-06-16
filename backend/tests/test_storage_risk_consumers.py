"""Tests for StorageConsumer and RiskConsumer.

Both consumers accept an injectable mock Kafka consumer so no broker is needed.
"""
from __future__ import annotations

from collections import namedtuple
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.consumers.risk_consumer import RiskConsumer
from app.consumers.storage_consumer import StorageConsumer
from app.models import DeviceReport, RiskAssessment, TelemetryPayload
from tests.conftest import sample_payload, suspicious_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ConsumerRecord = namedtuple(
    "ConsumerRecord",
    ["topic", "partition", "offset", "timestamp", "timestamp_type",
     "key", "value", "headers", "checksum",
     "serialized_key_size", "serialized_value_size", "serialized_header_size"],
    defaults=[None] * 12,
)


def _msg(payload_id: str) -> ConsumerRecord:
    return ConsumerRecord(topic="telemetry_events", partition=0, offset=0,
                          value={"payload_id": payload_id}, headers=[])


def _fake_consumer(messages: list) -> MagicMock:
    mc = MagicMock()
    mc.__iter__ = MagicMock(return_value=iter(messages))
    return mc


def _ingest(client, payload_id: str, **kwargs) -> None:
    resp = client.post("/api/v1/telemetry", json=sample_payload(payload_id=payload_id, **kwargs))
    assert resp.status_code == 202


def _set_status(app, payload_id: str, status: str) -> None:
    with app.state.session_factory() as s:
        r = s.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
        r.processing_status = status
        s.commit()


# ---------------------------------------------------------------------------
# StorageConsumer tests
# ---------------------------------------------------------------------------

def test_storage_consumer_normalizes_payload(client, app):
    """StorageConsumer calls NormalizationService and commits entities to the DB."""
    _ingest(client, "sc-norm-001")
    _set_status(app, "sc-norm-001", "ACCEPTED")

    sc = StorageConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([_msg("sc-norm-001")]),
    )
    sc.run()

    with app.state.session_factory() as s:
        dr = s.scalar(select(DeviceReport).where(DeviceReport.payload_id == "sc-norm-001"))
        assert dr is not None


def test_storage_consumer_skips_unknown_payload_id(app):
    """A message for a non-existent payload_id is silently skipped."""
    sc = StorageConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([_msg("ghost-sc-001")]),
    )
    sc.run()  # should not raise


def test_storage_consumer_skips_message_without_payload_id(app):
    """A message with no payload_id key is skipped without error."""
    bad = ConsumerRecord(topic="t", partition=0, offset=0, value={"junk": True}, headers=[])
    sc = StorageConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([bad]),
    )
    sc.run()  # should not raise


def test_storage_consumer_rollback_on_normalization_error(client, app):
    """If normalization raises, the session is rolled back and consumer continues."""
    _ingest(client, "sc-err-001")
    _set_status(app, "sc-err-001", "ACCEPTED")

    sc = StorageConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([_msg("sc-err-001")]),
    )
    with patch.object(sc.normalizer, "normalize", side_effect=RuntimeError("norm error")):
        sc.run()  # should not raise; error is logged


# ---------------------------------------------------------------------------
# RiskConsumer tests
# ---------------------------------------------------------------------------

def test_risk_consumer_scores_payload(client, app):
    """RiskConsumer scores a normalized payload and sets status=PROCESSED."""
    _ingest(client, "rc-score-001")
    _set_status(app, "rc-score-001", "ACCEPTED")

    rc = RiskConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([_msg("rc-score-001")]),
    )
    rc.run()

    with app.state.session_factory() as s:
        r = s.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "rc-score-001"))
        assert r.processing_status == "PROCESSED"
        assessment = s.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == "rc-score-001"))
        assert assessment is not None


def test_risk_consumer_marks_failed_on_scorer_error(client, app):
    """If the risk scorer raises, the payload is marked FAILED in the DB."""
    _ingest(client, "rc-fail-001")
    _set_status(app, "rc-fail-001", "ACCEPTED")

    rc = RiskConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([_msg("rc-fail-001")]),
    )
    with patch.object(rc.risk_scorer, "score", side_effect=RuntimeError("scorer boom")):
        rc.run()

    with app.state.session_factory() as s:
        r = s.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "rc-fail-001"))
        assert r.processing_status == "FAILED"
        assert "scorer boom" in (r.processing_error or "")


def test_risk_consumer_skips_unknown_payload_id(app):
    """A message for a non-existent payload_id is silently handled."""
    rc = RiskConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([_msg("ghost-rc-001")]),
    )
    rc.run()  # should not raise


def test_risk_consumer_skips_message_without_payload_id(app):
    """A message with no payload_id key is skipped without error."""
    bad = ConsumerRecord(topic="t", partition=0, offset=0, value={}, headers=[])
    rc = RiskConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([bad]),
    )
    rc.run()  # should not raise


def test_risk_consumer_high_risk_triggers_ai(client, app):
    """A high-risk payload (rooted + suspicious app) causes AI analysis to run."""
    _ingest(client, "rc-ai-001", rooted=True, apps=[suspicious_app()])
    _set_status(app, "rc-ai-001", "ACCEPTED")

    rc = RiskConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=_fake_consumer([_msg("rc-ai-001")]),
    )
    rc.run()

    with app.state.session_factory() as s:
        from app.models import AIRiskDecision
        decision = s.scalar(select(AIRiskDecision).where(AIRiskDecision.payload_id == "rc-ai-001"))
        assert decision is not None
