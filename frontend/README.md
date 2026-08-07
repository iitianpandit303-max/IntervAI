# IntervAI Frontend

React + Vite interview interface for the ABTalks AI Cohort Interview Agent.

## Local development

1. Copy the root `.env.example` to `frontend/.env` or create `frontend/.env` with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

2. Install and run:

```bash
npm install
npm run dev
```

The frontend expects the FastAPI backend on port `8000` by default.

## Current scope

- Supplied candidate profile selector
- Interview session initialization
- Conversational multi-turn interview room
- 8-question minimum progress indicator
- Loading and error handling
- Heuristic Pressure Mode visual state without changing the evaluator API contract
- Full Interview Readiness Report completion dashboard
- Live seven-domain Candidate Knowledge Map
- Current curriculum day, question type, difficulty, and Pressure Mode metadata

For production, set `VITE_API_BASE_URL` to the deployed FastAPI origin before running `npm run build`. See `../docs/DEPLOYMENT.md`.
