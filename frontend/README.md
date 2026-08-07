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

## Commit 13 scope

- Supplied candidate profile selector
- Interview session initialization
- Conversational multi-turn interview room
- 8-question minimum progress indicator
- Loading and error handling
- Heuristic Pressure Mode visual state without changing the evaluator API contract
- Minimal completion state

The full Knowledge Map and Interview Readiness Report visualization are intentionally deferred to Commit 14.
