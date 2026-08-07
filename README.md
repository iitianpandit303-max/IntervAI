# IntervAI — ABTalks AI Interview Agent

IntervAI is a modular technical interview agent for the ABTalks AI Cohort.

## Current milestone

Commits 1–16 establish:
- React + Vite frontend skeleton
- FastAPI backend skeleton
- supplied curriculum/candidate data loaders
- exact `POST /api/interview` contract
- session lifecycle with mocked, curriculum-grounded questions
- candidate intelligence priors derived from pass/fail/skip/attempt and cohort signals
- explicit UNKNOWN handling for mission days absent from sparse candidate profiles
- structured curriculum-grounded answer evaluation
- bounded adaptive RECOVER / PROBE / DEEPEN follow-ups
- selective Pressure Mode for strong engineering answers
- dynamic Candidate Knowledge Map with profile priors, interview evidence, confidence and topic-level mastery
- bounded structured interview memory with recent turns, rolling summary, strengths, open gaps and misconceptions
- deterministic Interview Readiness Report with overall readiness, rubric dimensions, strongest/weakest topics, revisit days, struggled questions and actionable next steps
- conversational React interview room using the exact evaluator POST contract
- live Knowledge Map and rich readiness dashboard through a hidden presentation-safe GET view
- judge-proof runtime hardening: strict request/response shapes, configurable CORS, bounded LLM retries and deployment smoke tests

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

## Commit 7 — Curriculum-grounded answer evaluation

Every candidate answer is now evaluated against the exact curriculum day, objective, question type, difficulty, and question text that produced it. The evaluator returns a validated 0–4 rubric for technical accuracy, conceptual understanding, engineering reasoning, implementation depth, and communication clarity, plus concise strengths, missing concepts, misconceptions, confidence, and a recommended future action (`RECOVER`, `PROBE`, `DEEPEN`, `PRESSURE`, or `SWITCH`). The evaluation is stored on the interview turn in SQLite. Empty answers are handled deterministically, while unavailable or malformed LLM evaluations produce neutral scores with `confidence=0.0` so later knowledge-map logic can ignore them safely. Commit 7 deliberately does not alter the next-question plan; adaptation is the next milestone.

## Commit 8 — Adaptive interview engine

Stored answer evaluations now affect the next turn. A bounded backend `AdaptivePolicy` normalizes evaluation evidence into `RECOVER`, `PROBE`, `DEEPEN`, or `SWITCH`. Reliable weak answers receive a simpler same-day diagnostic question, partial answers receive a focused probe, and strong answers can receive a deeper engineering follow-up. At the Commit 8 milestone, `PRESSURE` was intentionally normalized to `DEEPEN`; Commit 9 activates the dedicated pressure path. Adaptive follow-ups are inserted rather than replacing the original eight-question plan, preserving the deterministic four-day coverage guarantee. The engine caps adaptive inserts at two and never chains a follow-up directly from another follow-up. Low-confidence fallback evaluations do not alter the plan. Adaptive questions have their own curriculum-grounded prompt and deterministic fallback, so the behavior still works when no external LLM is configured.

## Commit 9 — Pressure Mode

IntervAI can now challenge strong answers instead of simply rewarding them with a harder question. `AdaptivePolicy` permits `PRESSURE` only for high-confidence, high-scoring answers with demonstrated engineering reasoning; weak, partial, or uncertain answers continue through the normal RECOVER / PROBE / DEEPEN paths. A separate `PressureModeStrategy` selects an assumption, alternative, counterfactual, or production-constraint challenge from the original question style, and a dedicated pressure prompt asks the LLM to challenge one concrete decision without becoming argumentative. Pressure questions are marked explicitly in session state and have their own counter. They consume the existing two-follow-up global budget and cannot chain directly from another adaptive question, preserving the original eight-question/four-day coverage plan and keeping the interview bounded at roughly 8–10 questions. If the LLM is unavailable or malformed, a deterministic professional pressure challenge is used instead.


## Commit 10 — Candidate Knowledge Map

IntervAI now maintains a persistent mastery map for RAG, Vector Databases, Prompt Engineering, Agentic AI, MCP, Deployment, and Production AI Systems. The map starts from deliberately low-confidence candidate-history priors and is updated after every reliable answer. A curriculum day may update multiple related areas, reflecting the overlap between real AI systems. Technical mastery uses accuracy, conceptual understanding, engineering reasoning, and implementation depth; communication is intentionally kept separate for the later readiness report. Evidence is weighted by evaluator confidence, question type, and difficulty, so a system-design or pressure answer carries more diagnostic value than a basic definition answer. `confidence=0` fallback evaluations never alter mastery. Each topic stores score, confidence, profile evidence, strong evidence, gaps, misconceptions, question count, and the most recent question that changed it.


## Commit 11 — Structured interview memory & context

IntervAI now separates the full persisted transcript from the compact context sent to the LLM. `InterviewSession.turns` remains the complete source of truth in SQLite, while a bounded `InterviewMemory` stores the last four turns, a deterministic rolling summary, observed strengths, unresolved gaps, misconceptions and curriculum days discussed. The Memory Manager also renders a compact Knowledge Map snapshot for question-generation context. Reliable evaluations update memory; `confidence=0` fallback evaluations never become remembered candidate evidence. Strong later evidence on the same curriculum day can close earlier same-day gaps. The memory context is supplied to planned-question generation, adaptive follow-ups, Pressure Mode and answer evaluation, allowing cross-turn references without sending an ever-growing raw transcript. Memory summarization is deterministic in this milestone, so it adds no extra LLM call per turn.


## Commit 12 — Interview Readiness Report

At completion, IntervAI now aggregates the full interview into a persistent rich report. Reliable answer evaluations drive technical accuracy, conceptual understanding, engineering reasoning, communication quality and answer depth scores; the Candidate Knowledge Map contributes topic mastery; weak answers, missing concepts and misconceptions identify struggled questions and curriculum days to revisit. Candidate-history failed/skipped days can appear as secondary revision signals but are never treated as live interview failures. The report stores overall score, readiness level, report confidence, strongest/weakest topics, topics to revise, revisit days, struggled questions and suggested preparation steps. The evaluator-facing response remains contract-safe and returns only `summary`, `strengths`, `gaps`, and `next`. Final aggregation is deterministic and ignores `confidence=0` fallback evaluations, so provider outages cannot fabricate readiness evidence.

## Commit 13 — React Interview Room

The frontend now provides the full candidate-to-interview flow using the existing `POST /api/interview` contract: supplied candidate selection, conversational messages, question progress, loading/error states, a lightweight Pressure Mode visual signal, and an interview-complete handoff. No additional frontend framework or evaluator-facing API fields were introduced.


## Commit 14 — Visual Knowledge Map and Readiness UI

The React demo now reads presentation-safe interview insights from `GET /api/interview?sessionId=...` while the required evaluator contract remains unchanged on `POST /api/interview`. The GET companion route is hidden from OpenAPI and exposes only live progress, the Candidate Knowledge Map, current-question metadata, and the persisted final readiness report.


## Commit 15 — Judge-proofing and deployment hardening

The evaluator path is now hardened for submission. Non-final `POST /api/interview` responses exclude the optional `feedback` field so they match the supplied start/turn examples exactly, and request validation enforces exactly one of `candidate` or `message`. Deployment CORS origins are environment-driven, `/health` reports whether the API is using a configured LLM or deterministic fallback without exposing secrets, and the OpenAI-compatible client has a bounded retry budget for transient 429/5xx/transport failures while failing fast on full timeouts. JSON parsing can recover a single object from harmless provider preamble text without accepting malformed structures. A contract-level judge simulation now runs all 20 supplied candidate profiles through complete interviews and verifies 8+ questions, 4+ curriculum days, the exact final feedback fields, and the hidden frontend GET remaining absent from OpenAPI. `scripts/judge_smoke_test.py` performs the same critical checks against a live deployment, and deployment/checklist documentation plus a Render backend blueprint are included.


## Commit 16 — Production release and submission preparation

The final release milestone adds environment-configurable SQLite storage for deployment, a real-provider structured LLM probe, a one-command release checker, a backend Dockerfile, GitHub Actions CI, AI workflow documentation, a concise demo script, and a submission template. The evaluator POST contract and interview intelligence remain unchanged. Use `python scripts/llm_probe.py` after configuring a real OpenAI-compatible provider, then use `python scripts/release_check.py --base-url <PUBLIC_BACKEND_URL>` for the final tests/build/live smoke-test gate.
