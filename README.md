# IntervAI — ABTalks AI Interview Agent

IntervAI is a modular technical interview agent for the ABTalks AI Cohort.

## Current milestone

Commits 1–6 establish:
- React + Vite frontend skeleton
- FastAPI backend skeleton
- supplied curriculum/candidate data loaders
- exact `POST /api/interview` contract
- session lifecycle with mocked, curriculum-grounded questions
- candidate intelligence priors derived from pass/fail/skip/attempt and cohort signals
- explicit UNKNOWN handling for mission days absent from sparse candidate profiles

Adaptive answer evaluation is intentionally deferred to later commits.

## Run backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend: `http://127.0.0.1:8000`

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## Commit 5 — Curriculum-aware interview planning

The deterministic planner now converts candidate learning signals into an eight-question interview plan that covers at least four curriculum days. It prefers completed missions, prioritizes repeated-attempt topics for deeper verification, spreads anchor questions across curriculum modules where possible, rotates concept/implementation/debugging/trade-off/system-design styles, and validates coverage before a session starts. No LLM is used yet; this keeps the evaluator contract stable before adaptive generation is introduced.

## Commit 6 — Structured LLM question generation

IntervAI now has a provider-neutral OpenAI-compatible LLM gateway. The deterministic planner still owns curriculum day, question type, difficulty, purpose, and coverage; the model is only allowed to rewrite the current plan slot into natural interviewer language. Generated output is validated with Pydantic before it enters session state. If the provider is missing, times out, returns invalid JSON, or violates the schema, the original deterministic question is retained automatically so `/api/interview` remains usable. Questions are generated just in time rather than generating the entire interview up front.

Configure an OpenAI-compatible provider with `INTERVAI_LLM_BASE_URL`, `INTERVAI_LLM_API_KEY`, and `INTERVAI_LLM_MODEL`. Leaving them blank intentionally enables safe deterministic fallback mode.
