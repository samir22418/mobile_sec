"""
Integration tests for TelemetryConsumer.

Uses a real SQLite DB (via the `app` and `client` fixtures) and a mock
Kafka consumer/producer so no broker is required.  The consumer is driven
through its public `run()` method with an injectable fake consumer that
yields a finite list of messages and then raises StopIteration.
"""
from __future__ import annotations

from collections import namedtuple
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.consumers.telemetry_consumer import TelemetryConsumer
from app.kafka import MAX_RETRIES
from app.models import TelemetryPayload
from tests.conftest import sample_payload

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


def _make_message(payload_id: str, retry_count: int = 0) -> ConsumerRecord:
    headers = [(b"retry-count", str(retry_count).encode())] if retry_count else []
    return ConsumerRecord(
        topic="telemetry_events",
        partition=0,
        offset=0,
        value={"payload_id": payload_id},
        headers=headers,
    )


def _make_kafka_mocks(messages: list) -> tuple:
    """Return (mock_consumer, mock_producer, commit_spy)."""
    mock_consumer = MagicMock()
    mock_consumer.__iter__ = MagicMock(return_value=iter(messages))
    mock_consumer.close = MagicMock()
    mock_consumer.commit = MagicMock()
    mock_producer = MagicMock()
    mock_producer.send = MagicMock()
    mock_producer.flush = MagicMock()
    return mock_consumer, mock_producer


def _ingest_payload(client, payload_id: str, **kwargs) -> None:
    resp = client.post("/api/v1/telemetry", json=sample_payload(payload_id=payload_id, **kwargs))
    assert resp.status_code == 202


def _build_consumer(app) -> TelemetryConsumer:
    return TelemetryConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
    )


# ---------------------------------------------------------------------------
# Test 1: end-to-end processing of a single payload
# ---------------------------------------------------------------------------

def test_consumer_processes_payload_end_to_end(client, app):
    """Consumer runs TelemetryWorker.process_one() and commits the offset."""
    _ingest_payload(client, "cns-e2e-001")

    # Revert to ACCEPTED so the consumer has work to do (inline was true)
    session = app.state.session_factory()
    try:
        r = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "cns-e2e-001"))
        r.processing_status = "ACCEPTED"
        session.commit()
    finally:
        session.close()

    mock_consumer, mock_producer = _make_kafka_mocks([_make_message("cns-e2e-001")])
    consumer = _build_consumer(app)
    consumer.run.__func__  # just ensure it exists
    # Run with injected mocks
    tc = TelemetryConsumer(
        app.state.settings,
        app.state.session_factory,
        app.state.raw_store,
        consumer=mock_consumer,
        producer=mock_producer,
    )
    tc.run()

    # Offset must be committed after successful processing
    mock_consumer.commit.assert_called()
    # DB record should be PROCESSED
    session = app.state.session_factory()
    try:
        r = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "cns-e2e-001"))
        assert r.processing_status == "PROCESSED"
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 2: already-PROCESSED payload is skipped (idempotency)
# ---------------------------------------------------------------------------

def test_consumer_skips_already_processed_payload(client, app):
    """Already-PROCESSED records are not re-processed — offset is committed."""
    _ingest_payload(client, "cns-idem-001")  # inline=True → becomes PROCESSED immediately

    mock_consumer, mock_producer = _make_kafka_mocks([_make_message("cns-idem-001")])
    tc = TelemetryConsumer(
        app.state.settings, app.state.session_factory, app.state.raw_store,
        consumer=mock_consumer, producer=mock_producer,
    )
    with patch.object(tc._worker, "process_one") as mock_worker:
        tc.run()
        mock_worker.assert_not_called()

    mock_consumer.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3: worker failure triggers re-queue with incremented retry count
# ---------------------------------------------------------------------------

def test_consumer_requeues_on_worker_failure(client, app):
    """On first failure (retry_count=0) the message is re-published with retry_count=1."""
    _ingest_payload(client, "cns-retry-001")

    session = app.state.session_factory()
    try:
        r = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "cns-retry-001"))
        r.processing_status = "ACCEPTED"
        session.commit()
    finally:
        session.close()

    mock_consumer, mock_producer = _make_kafka_mocks([_make_message("cns-retry-001", retry_count=0)])
    tc = TelemetryConsumer(
        app.state.settings, app.state.session_factory, app.state.raw_store,
        consumer=mock_consumer, producer=mock_producer,
    )
    with patch.object(tc._worker, "process_one", side_effect=RuntimeError("transient error")):
        tc.run()

    # Should re-publish to the same topic with retry-count=1 header
    mock_producer.send.assert_called_once()
    call_args = mock_producer.send.call_args
    assert call_args[0][0] == app.state.settings.kafka_telemetry_topic
    assert call_args[0][1] == {"payload_id": "cns-retry-001"}
    headers = dict(call_args[1]["headers"])
    assert headers[b"retry-count"] == b"1"

    # Offset committed despite failure (don't get stuck)
    mock_consumer.commit.assert_called()


# ---------------------------------------------------------------------------
# Test 4: DLQ after MAX_RETRIES exceeded
# ---------------------------------------------------------------------------

def test_consumer_sends_to_dlq_after_max_retries(client, app):
    """When retry_count == MAX_RETRIES the message goes to the DLQ and DB status=FAILED_DLQ."""
    _ingest_payload(client, "cns-dlq-001")

    session = app.state.session_factory()
    try:
        r = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "cns-dlq-001"))
        r.processing_status = "ACCEPTED"
        session.commit()
    finally:
        session.close()

    mock_consumer, mock_producer = _make_kafka_mocks(
        [_make_message("cns-dlq-001", retry_count=MAX_RETRIES)]
    )
    tc = TelemetryConsumer(
        app.state.settings, app.state.session_factory, app.state.raw_store,
        consumer=mock_consumer, producer=mock_producer,
    )
    with patch.object(tc._worker, "process_one", side_effect=RuntimeError("permanent error")):
        tc.run()

    # DLQ publish
    mock_producer.send.assert_called_once()
    dlq_call = mock_producer.send.call_args
    expected_dlq_topic = f"{app.state.settings.kafka_telemetry_topic}.dlq"
    assert dlq_call[0][0] == expected_dlq_topic
    assert dlq_call[0][1]["payload_id"] == "cns-dlq-001"

    # DB record marked FAILED_DLQ
    session = app.state.session_factory()
    try:
        r = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "cns-dlq-001"))
        assert r.processing_status == "FAILED_DLQ"
        assert "[DLQ]" in r.processing_error
    finally:
        session.close()

    # Offset committed so consumer doesn't get stuck
    mock_consumer.commit.assert_called()


# ---------------------------------------------------------------------------
# Test 5: message without payload_id is safely skipped
# ---------------------------------------------------------------------------

def test_consumer_skips_message_without_payload_id(app):
    """A message with no payload_id is committed and discarded without crashing."""
    bad_msg = ConsumerRecord(
        topic="telemetry_events", partition=0, offset=0,
        value={"unexpected": "field"}, headers=[],
    )
    mock_consumer, mock_producer = _make_kafka_mocks([bad_msg])
    tc = TelemetryConsumer(
        app.state.settings, app.state.session_factory, app.state.raw_store,
        consumer=mock_consumer, producer=mock_producer,
    )
    with patch.object(tc._worker, "process_one") as mock_worker:
        tc.run()
        mock_worker.assert_not_called()

    mock_consumer.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6: unknown payload_id (not in DB) is committed without crashing
# ---------------------------------------------------------------------------

def test_consumer_handles_unknown_payload_id(app):
    """A message for a non-existent payload_id fails in process_one and gets re-queued."""
    mock_consumer, mock_producer = _make_kafka_mocks([_make_message("ghost-payload-xyz")])
    tc = TelemetryConsumer(
        app.state.settings, app.state.session_factory, app.state.raw_store,
        consumer=mock_consumer, producer=mock_producer,
    )
    tc.run()

    # process_one raises ValueError for missing payload → retry re-published (or DLQ)
    # Either way, commit is called and consumer does not crash
    mock_consumer.commit.assert_called()


# ---------------------------------------------------------------------------
# Test 7: throughput — 20 payloads processed in one consumer run
# ---------------------------------------------------------------------------

def test_consumer_throughput_20_payloads(client, app):
    """20 unique payloads submitted → all end up PROCESSED after one consumer run."""
    n = 20
    ids = [f"throughput-{i:03d}" for i in range(n)]

    # Submit all payloads via HTTP (process_inline=True → PROCESSED immediately in test fixture)
    for pid in ids:
        _ingest_payload(client, pid)

    # Revert all to ACCEPTED to simulate async pipeline
    session = app.state.session_factory()
    try:
        for pid in ids:
            r = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == pid))
            if r:
                r.processing_status = "ACCEPTED"
        session.commit()
    finally:
        session.close()

    messages = [_make_message(pid) for pid in ids]
    mock_consumer, mock_producer = _make_kafka_mocks(messages)
    tc = TelemetryConsumer(
        app.state.settings, app.state.session_factory, app.state.raw_store,
        consumer=mock_consumer, producer=mock_producer,
    )
    tc.run()

    # All 20 must be PROCESSED
    session = app.state.session_factory()
    try:
        statuses = {
            r.payload_id: r.processing_status
            for r in session.scalars(
                select(TelemetryPayload).where(TelemetryPayload.payload_id.in_(ids))
            ).all()
        }
    finally:
        session.close()

    failed = [pid for pid in ids if statuses.get(pid) != "PROCESSED"]
    assert not failed, f"Not all payloads processed: {failed}"
    # Commit called once per message
    assert mock_consumer.commit.call_count == n
