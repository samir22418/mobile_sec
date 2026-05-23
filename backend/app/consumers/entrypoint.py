import logging
from threading import Thread
from typing import Callable

from app.config import load_settings, Settings
from app.kafka import get_consumer
from app.database import make_session_factory
from app.services.raw_store import RawPayloadStore

from app.consumers.risk_consumer import RiskConsumer
from app.consumers.storage_consumer import StorageConsumer

logger = logging.getLogger(__name__)

def run_consumer_loop(consumer_class: type, settings: Settings, **kwargs) -> None:
    consumer_instance = consumer_class(settings=settings, **kwargs)
    try:
        consumer_instance.run()
    except Exception as e:
        logger.error(f"Consumer {consumer_class.__name__} failed: {e}")

def main() -> None:
    settings = load_settings()
    session_factory = make_session_factory(settings.database_url)
    raw_store = RawPayloadStore(settings.raw_payload_dir)
    
    threads = []
    consumers = [
        (StorageConsumer, {"session_factory": session_factory, "raw_store": raw_store}),
        (RiskConsumer, {"session_factory": session_factory, "raw_store": raw_store}),
    ]
    
    for consumer_class, kwargs in consumers:
        t = Thread(target=run_consumer_loop, args=(consumer_class, settings), kwargs=kwargs, daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"Started consumer thread: {consumer_class.__name__}")
        
    for t in threads:
        t.join()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
