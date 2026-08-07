# Judge-Proof Checklist

Run this list before submitting or after every deployment change.

## Required contract

- `POST /api/interview` starts with `{ "sessionId": "...", "candidate": { ... } }`.
- Later calls use `{ "sessionId": "...", "message": "..." }`.
- Non-final responses contain exactly `reply` and `done`.
- Final response contains exactly `reply`, `done`, and `feedback`.
- `feedback` contains exactly `summary`, `strengths`, `gaps`, and `next`.
- One request cannot contain both `candidate` and `message`.
- Unknown conversation sessions return HTTP 404.
- The frontend-only `GET /api/interview` route stays hidden from OpenAPI.

## Interview guarantees

- At least 8 answered questions.
- At least 4 distinct curriculum days.
- Adaptive inserts never replace the deterministic coverage plan.
- Total adaptive/pressure insert budget remains bounded.
- `confidence=0` fallback evaluations never alter candidate mastery or final readiness evidence.

## Reliability

- `GET /health` returns `status=ok`.
- LLM not configured: deterministic fallback still completes a valid interview.
- LLM timeout: the current turn falls back rather than blocking indefinitely.
- Transient provider 429/5xx: one bounded retry is allowed by default.
- SQLite tests pass on Windows with no locked database files.
- Backend CORS includes the deployed frontend origin.

## Final commands

```bash
cd backend
python -m pytest -q
cd ..
python scripts/judge_smoke_test.py --base-url http://127.0.0.1:8000
```

For the frontend:

```bash
cd frontend
npm install
npm run build
```

Do not submit until the test suite, live smoke test, and production frontend build all pass.
