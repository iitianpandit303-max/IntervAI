# IntervAI — ABTalks AI Interview Agent

IntervAI is a modular technical interview agent for the ABTalks AI Cohort.

## Current milestone

Commits 1–3 establish:
- React + Vite frontend skeleton
- FastAPI backend skeleton
- supplied curriculum/candidate data loaders
- exact `POST /api/interview` contract
- session lifecycle with mocked, curriculum-grounded questions

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
