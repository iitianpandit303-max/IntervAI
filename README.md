# IntervAI — ABTalks AI Interview Agent

IntervAI is a modular technical interview agent for the ABTalks AI Cohort.

## Current milestone

Commits 1–4 establish:
- React + Vite frontend skeleton
- FastAPI backend skeleton
- supplied curriculum/candidate data loaders
- exact `POST /api/interview` contract
- session lifecycle with mocked, curriculum-grounded questions
- candidate intelligence priors derived from pass/fail/skip/attempt and cohort signals
- explicit UNKNOWN handling for mission days absent from sparse candidate profiles

LLM integration and adaptive evaluation are intentionally deferred to later commits.

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
