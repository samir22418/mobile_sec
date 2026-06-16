from __future__ import annotations

import logging
import signal
import sys
import threading
import time

from app.config import load_settings
from app.consumers.telemetry_consumer import TelemetryConsumer
from app.database import init_db, make_session_factory
from app.services.raw_store import RawPayloadStore

logger = logging.getLogger(__name__)

_RESTART_DELAY_SECONDS = 5
_MAX_RESTART_ATTEMPTS = 10


def _run_with_supervisor(consumer: TelemetryConsumer, stop_event: threading.Event) -> None:
    """Start the consumer in a thread and restart it if it crashes unexpectedly."""
    attempts = 0
    while not stop_event.is_set():
        attempts += 1
        if attempts > _MAX_RESTART_ATTEMPTS:
            logger.error("Consumer crashed %d times — giving up", attempts - 1)
            stop_event.set()
            break

        t = threading.Thread(target=consumer.run, daemon=True, name="telemetry-consumer")
        t.start()
        logger.info("Consumer thread started (attempt %d)", attempts)
        t.join()

        if stop_event.is_set():
            break

        logger.warning("Consumer thread exited unexpectedly — restarting in %ds", _RESTART_DELAY_SECONDS)
        time.sleep(_RESTART_DELAY_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        stream=sys.stdout,
    )

    settings = load_settings()
    session_factory = make_session_factory(settings.database_url)
    init_db(session_factory)
    raw_store = RawPayloadStore(settings.raw_payload_dir)

    consumer = TelemetryConsumer(settings, session_factory, raw_store)
    stop_event = threading.Event()

    def _on_signal(signum: int, frame: object) -> None:
        logger.info("Received signal %d — shutting down gracefully", signum)
        consumer.stop()
        stop_event.set()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    logger.info("AEGIS consumer starting — database=%s topic=%s", settings.database_url[:40], settings.kafka_telemetry_topic)
    _run_with_supervisor(consumer, stop_event)
    logger.info("AEGIS consumer exited")


if __name__ == "__main__":
    main()
