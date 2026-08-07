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
INTERVAI_SESSION_DB_PATH=
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


## Verify the real LLM before deploying

After setting the backend LLM variables locally, run:

```bash
python scripts/llm_probe.py
```

The probe prints only the configured model name and pass/fail status; it never prints the API key. If the probe fails, fix the provider configuration before relying on AI mode. The application can still operate in deterministic fallback mode.

## Persistent session state

By default SQLite is stored at `backend/intervai_sessions.db`. On a host that offers a persistent disk, set `INTERVAI_SESSION_DB_PATH` to a writable path on that disk. For the evaluator, run a single backend instance/worker so all calls for a `sessionId` reach the same SQLite store.

## One-command release check

From the repository root:

```bash
python scripts/release_check.py --base-url https://your-backend.example.com
```

This runs the backend test suite, the Vite production build, and the live evaluator smoke test. Before a public URL exists, omit `--base-url`.

## Container option

A production-safe backend Dockerfile is available at `backend/Dockerfile`. Build it from the repository root so both `backend/` and `data/` are available in the image context.
