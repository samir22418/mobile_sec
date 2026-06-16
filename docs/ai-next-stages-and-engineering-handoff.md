# AEGIS AI Next Stages And Engineering Handoff

## Current AI Shape

- Backend local analyzers are separated from chatbot AI.
- Local analyzers own automated security judgment:
  - `logs_llm_analyst`
  - `telemetry_llm_analyst`
  - `risk_llm_scorer`
- Shieldy/OpenRouter owns the analyst chatbot only.
- Every model call or AI decision is audited in backend storage.
- The dashboard AI Center shows model runs, risk decisions, Shieldy chat, and engineering handoff notes.

## Replaceable AI Interfaces

- Local analyzer engineers should work behind `LocalAnalyzerProvider` in `backend/app/ai/analyzer.py`.
- Chatbot engineers should work inside `backend/app/shieldy/`:
  - `models.py`: model role registry.
  - `security_gate.py`: prompt-injection and safety rules.
  - `fast_router.py`: route selection.
  - `prompts.py`: system prompt.
  - `providers.py`: OpenRouter or future provider clients.
  - `agent.py`: orchestration and action filtering.
- UI engineers can replace Streamlit later without changing API contracts.

## Next Stages

1. Real local model integration:
   - Configure Ollama or another local runtime.
   - Add JSON-schema constrained prompts for logs, telemetry, and risk scoring.
   - Build evaluation fixtures for benign, suspicious, and critical payloads.

2. AI evaluation set:
   - Create labeled payload/log scenarios.
   - Measure false positives, false negatives, score drift, invalid JSON rate, and latency.
   - Keep deterministic baseline as the comparison point.

3. Chatbot maturity:
   - Add durable chat history browsing.
   - Add analyst identity beyond token hash.
   - Add more confirmed actions only after audit tables are stable.

4. Frontend migration decision:
   - Keep Streamlit for MVP and demos.
   - Move to React/Next.js when the dashboard needs role-based UX, richer tables, live updates, or long-lived chat sessions.

5. Production hardening:
   - Move SQLite to Postgres.
   - Run workers out of process.
   - Add model timeout budgets, retries, circuit breakers, and per-role enable flags.
   - Add OpenRouter usage/cost tracking.

## AI Engineer Work Packages

- Prompt engineer: improve role prompts and output schemas.
- Model engineer: choose local models and quantization/runtime settings.
- Evaluation engineer: build payload/log benchmark set and scoring dashboards.
- Safety engineer: expand Shieldy safety gate and action policy tests.
- Data engineer: prepare analytics tables for model quality and analyst feedback loops.
