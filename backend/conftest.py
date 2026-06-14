from __future__ import annotations

import os

# Set AEGIS_ENV=dev before any sub-conftest or test module is imported.
#
# main.py creates a module-level `app = create_app()` so uvicorn can import it
# directly.  load_settings() raises in production mode when tokens or the
# console key are not configured.  Tests bypass load_settings() entirely by
# passing explicit Settings objects to create_app(), but that module-level call
# still fires as a side effect of `from app.main import create_app`.
#
# This module-level setdefault runs during the import of this root conftest,
# which pytest processes before the tests/ sub-conftest — so the env var is
# present by the time app.main is imported.
os.environ.setdefault("AEGIS_ENV", "dev")
