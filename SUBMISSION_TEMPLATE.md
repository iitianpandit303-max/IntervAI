# IntervAI — ViCodathon Submission Template

Replace every `<...>` placeholder before submitting.

## Project

**Name:** IntervAI — Adaptive Technical Interview Engine  
**Problem:** The Interview Agent  
**Repository:** <GITHUB_REPOSITORY_URL>  
**Live application:** <FRONTEND_URL>  
**Evaluator backend:** <BACKEND_URL>  
**Required endpoint:** `<BACKEND_URL>/api/interview`

## One-line pitch

IntervAI is a curriculum-grounded technical interviewer that adapts its depth, follow-ups, and engineering pressure to the candidate's learning history and live answers.

## Core behavior

- personalized from supplied candidate profile signals;
- at least 8 questions covering at least 4 curriculum days;
- curriculum-grounded concept, implementation, debugging, trade-off, and system-design questions;
- contextual RECOVER / PROBE / DEEPEN follow-ups;
- Pressure Mode for strong engineering answers;
- persistent session memory;
- dynamic Candidate Knowledge Map;
- structured Interview Readiness Report;
- deterministic fallback when the LLM provider is unavailable.

## API contract

Start:

```json
{
  "sessionId": "abc-123",
  "candidate": { "...": "provided candidate object" }
}
```

Continue:

```json
{
  "sessionId": "abc-123",
  "message": "candidate answer"
}
```

Final feedback contains `summary`, `strengths`, `gaps`, and `next`.

## Validation performed

Before submission, paste the final results here:

- Backend tests: `<PASS_COUNT> passed`
- Frontend production build: `<PASS/FAIL>`
- Public evaluator smoke test: `<PASS/FAIL>`
- Public LLM mode from `/health`: `<configured/deterministic-fallback>`
- Smoke-test question count: `<N>`
- Smoke-test curriculum-day count: `<N>`

## Architecture

React + Vite frontend → FastAPI `/api/interview` → deterministic Interview Orchestrator → OpenAI-compatible LLM gateway + curriculum/candidate JSON → SQLite session state.

## AI workflow

See `docs/AI_WORKFLOW.md` for prompt roles, structured output validation, fallback behavior, and the deterministic-vs-LLM responsibility split.
