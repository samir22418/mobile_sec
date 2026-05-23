# Anas Backend Migration Review

## Source Reviewed

Anas's folder was treated as reference material, not as a replacement for the
active backend. The active backend is already synchronous FastAPI + SQLAlchemy
with local SQLite defaults, audited AI stubs, enrollment-token support, and the
Android connect-device flow.

## Migrated

- Local telemetry rate limiting from Anas's `rate_limiter` idea, adapted to the
  current synchronous backend and app settings.
- Stronger log redaction patterns for API keys, generic secrets, credit-card-like
  numbers, and SSN-like values.
- Richer AI evidence bundles with suspicious app counts, log signal counts, and
  recent risk history for the same device.
- Useful dashboard concepts from Anas's Dash UI: fleet KPIs, high-risk count,
  average risk, risk distribution, priority devices, and risk trend. These were
  adapted into the existing Streamlit dashboard instead of replacing it.

## Not Migrated

- Async backend rewrite: our active backend is intentionally simpler and already
  tested end to end.
- Async idempotency helper: duplicate detection already exists in
  `IngestionService` and is covered by tests.
- Direct OpenAI provider: real LLM provider integration is a later phase; the
  current project keeps AI behind an audited stub.
- Extra Kafka consumers for logs/actions: useful later, but too much production
  infrastructure for the local MVP.
- Dash framework and heavy dashboard dependencies: the useful ideas were migrated
  into Streamlit so the active dashboard keeps payload drill-down and feedback.
- Duplicate risk matrix rewrite: the current normalized-data risk scorer is
  already integrated with persistence, API responses, and tests.

## Validation

- `python -m pytest` in `backend`: 23 passed.
- `python backend\scripts\check_pipeline.py`: pipeline validation successful.
