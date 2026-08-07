# Deployment Notes

IntervAI has two deployable parts: a FastAPI backend and a Vite static frontend.

## Backend environment

Configure these variables on the backend host:

```env
INTERVAI_LLM_BASE_URL=
INTERVAI_LLM_API_KEY=
INTERVAI_LLM_MODEL=
INTERVAI_LLM_TIMEOUT_SECONDS=20
INTERVAI_LLM_MAX_RETRIES=1
INTERVAI_CORS_ORIGINS=https://your-frontend.example.com
```

The LLM variables may be left blank for deterministic fallback mode. `INTERVAI_CORS_ORIGINS` accepts a comma-separated list and should contain every deployed frontend origin that needs browser access.

Backend start command from repository root:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Health check:

```text
GET /health
```

## Frontend environment

Create a production frontend environment value:

```env
VITE_API_BASE_URL=https://your-backend.example.com
```

Then build:

```bash
cd frontend
npm install
npm run build
```

Deploy `frontend/dist` with any static host.

## Post-deployment validation

From the repository root, run:

```bash
python scripts/judge_smoke_test.py --base-url https://your-backend.example.com
```

The script checks the health endpoint, exact evaluator start/final shapes, successful completion, 8+ answered questions, and 4+ curriculum days.
