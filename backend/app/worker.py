from __future__ import annotations

import argparse
import time

from app.config import load_settings
from app.database import init_db, make_session_factory
from app.services.raw_store import RawPayloadStore
from app.services.worker import TelemetryWorker


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AEGIS telemetry worker.")
    parser.add_argument("--once", action="store_true", help="Process one pending batch and exit.")
    args = parser.parse_args()

    settings = load_settings()
    session_factory = make_session_factory(settings.database_url)
    init_db(session_factory)
    worker = TelemetryWorker(session_factory, RawPayloadStore(settings.raw_payload_dir))

    if args.once:
        count = worker.process_pending()
        print(f"processed={count}")
        return

    print("AEGIS worker started")
    while True:
        count = worker.process_pending()
        if count:
            print(f"processed={count}")
        time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
