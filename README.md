# IntervAI — Adaptive Technical Interview Engine

> **ViCodathon · Problem Statement 2 — The Interview Agent**

IntervAI is a curriculum-grounded AI technical interviewer built for the **ABTalks 31-day AI Cohort**.  
Instead of asking a fixed list of questions, it adapts the interview based on the candidate's learning history and live answers.

**Live App:** https://intervai.iitianpandit303.workers.dev/  
**API:** https://intervai-f9nj.onrender.com  
**Evaluator Endpoint:** `POST https://intervai-f9nj.onrender.com/api/interview`  
**Repository:** https://github.com/iitianpandit303-max/IntervAI

---

## Why IntervAI?

A normal interview chatbot usually follows:

```text
Question → Answer → Next fixed question
```

IntervAI follows:

```text
Candidate Profile
      ↓
Curriculum-grounded Interview Plan
      ↓
Question
      ↓
Candidate Answer
      ↓
Structured Evaluation
      ↓
Knowledge Map + Memory Update
      ↓
Adaptive Decision
 ┌────────┼─────────┬──────────┐
 ↓        ↓         ↓          ↓
RECOVER  PROBE    DEEPEN    PRESSURE
 └────────┴─────────┴──────────┘
      ↓
Next Interview Turn
```

The result is an interview that behaves more like a technical interviewer than a scripted questionnaire.

---

## Core Features

### 1. Candidate-aware interview planning

IntervAI uses the supplied candidate profile signals:

- completed missions
- failed missions
- skipped missions
- attempt counts
- commit consistency
- first-try completion
- job role
- years of experience

Mission days absent from a sparse candidate profile are treated as **unknown**, not failed.

### 2. Deterministic coverage guarantee

The backend guarantees:

- **minimum 8 questions**
- **minimum 4 different curriculum days**
- bounded interview length
- no accidental loss of curriculum coverage when follow-ups are inserted

The LLM cannot override these rules.

### 3. Multiple technical question styles

Questions can test:

- concepts
- implementation
- debugging
- engineering trade-offs
- system design
- contextual follow-ups

### 4. Adaptive follow-ups

Every answer is evaluated and can lead to one of four normal actions:

- **RECOVER** — simplify and diagnose the missing foundation
- **PROBE** — target a specific missing concept
- **DEEPEN** — increase technical depth
- **SWITCH** — continue to the next planned curriculum topic

### 5. Pressure Mode

Strong answers can trigger a challenge rather than an easy acknowledgement.

Example:

> Candidate: “I would use a managed vector database.”

> IntervAI: “If the dataset fits comfortably on one machine and PostgreSQL already exists in the stack, why introduce another managed service?”

Pressure Mode can challenge:

- assumptions
- alternative approaches
- counterfactual scenarios
- production constraints

It is deliberately bounded so the interview remains professional and finite.

### 6. Curriculum-grounded answer evaluation

Answers are evaluated against the specific curriculum day and learning objectives using a structured rubric:

- technical accuracy
- conceptual understanding
- engineering reasoning
- implementation depth
- communication clarity

The evaluator also extracts:

- strong points
- missing concepts
- misconceptions
- confidence
- recommended next action

### 7. Candidate Knowledge Map

The interview continuously updates mastery for:

- RAG
- Vector Databases
- Prompt Engineering
- Agentic AI
- MCP
- Deployment
- Production AI Systems

Each topic maintains both a **mastery score** and **evidence confidence**.

A system-design or pressure answer contributes more evidence than a simple definition answer.

### 8. Structured interview memory

IntervAI separates:

```text
Full Transcript → persisted in SQLite
Working Memory  → bounded context sent to the LLM
```

Working memory contains:

- recent turns
- observed strengths
- unresolved gaps
- misconceptions
- curriculum days discussed
- Knowledge Map snapshot
- deterministic rolling summary

This preserves context without sending an ever-growing raw transcript to the model.

### 9. Interview Readiness Report

At completion, IntervAI generates:

- overall score
- readiness level
- report confidence
- technical accuracy
- conceptual understanding
- engineering reasoning
- communication quality
- answer depth
- strongest topics
- weakest topics
- topics to revise
- curriculum days to revisit
- questions where the candidate struggled
- actionable next preparation steps

### 10. Graceful AI fallback

IntervAI is deliberately not dependent on a perfect LLM response.

If the provider:

- times out
- returns malformed JSON
- becomes unavailable
- hits a transient failure

the backend falls back to deterministic interview behavior instead of breaking the evaluator flow.

---

## Architecture

```text
┌───────────────────────────────────────────────┐
│              React + Vite Frontend            │
│ Interview Room · Knowledge Map · Final Report │
└───────────────────────┬───────────────────────┘
                        │
                        │ POST /api/interview
                        ▼
┌───────────────────────────────────────────────┐
│                 FastAPI Backend               │
│                                               │
│  API Contract                                 │
│       ↓                                       │
│  Interview Orchestrator                       │
│       ↓                                       │
│  Candidate Analyzer ─ Curriculum Repository   │
│       ↓                                       │
│  Interview Planner + Coverage Policy          │
│       ↓                                       │
│  Structured LLM Gateway                       │
│       ↓                                       │
│  Answer Evaluator                             │
│       ↓                                       │
│  Adaptive Policy / Pressure Mode              │
│       ↓                                       │
│  Knowledge Map + Memory Manager               │
│       ↓                                       │
│  Interview Readiness Report                   │
│                                               │
│                  SQLite                       │
└───────────────────────────────────────────────┘
                        │
                        ▼
                Gemini 3.6 Flash
        through OpenAI-compatible API
```

---

## Design Principle

### LLM intelligence vs deterministic guarantees

IntervAI intentionally splits responsibilities.

**The LLM handles:**

- natural question wording
- answer interpretation
- misconception detection
- follow-up generation
- engineering challenges

**Backend code guarantees:**

- 8+ questions
- 4+ curriculum days
- session state
- question limits
- coverage
- bounded follow-ups
- valid response schemas
- final completion rules
- deterministic fallback

This prevents model variability from violating the hackathon contract.

---

## Why no vector database?

The supplied curriculum contains only 31 structured days with explicit:

- day numbers
- modules
- tools
- objectives

A vector database would increase complexity without improving retrieval enough to justify it.

IntervAI therefore uses deterministic indexed curriculum lookup and spends its AI complexity where it matters: **adaptation, evaluation, memory, and engineering judgment**.

---

## Required API Contract

### Start interview

```http
POST /api/interview
Content-Type: application/json
```

```json
{
  "sessionId": "abc-123",
  "candidate": {
    "...": "supplied candidate object"
  }
}
```

Example response:

```json
{
  "reply": "Welcome. Let's begin your interview...",
  "done": false
}
```

### Continue interview

```json
{
  "sessionId": "abc-123",
  "message": "Candidate's latest answer"
}
```

Response:

```json
{
  "reply": "Next interviewer response...",
  "done": false
}
```

### Final response

```json
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": [],
    "gaps": [],
    "next": []
  }
}
```

---

## Tech Stack

### Frontend
- React
- Vite
- Cloudflare Workers Static Assets

### Backend
- Python
- FastAPI
- Pydantic
- SQLite
- HTTPX
- Uvicorn

### AI
- Gemini 3.6 Flash
- OpenAI-compatible API
- structured JSON outputs
- Pydantic validation
- deterministic fallback paths

### Deployment
- Frontend: Cloudflare Workers
- Backend: Render
- Source: GitHub
- CI: GitHub Actions

---

## Repository Structure

```text
IntervAI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── config/
│   │   ├── llm/
│   │   ├── models/
│   │   ├── prompts/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── strategies/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── pages/
│   └── package.json
│
├── data/
│   ├── curriculum.json
│   └── candidates.json
│
├── docs/
│   ├── AI_WORKFLOW.md
│   ├── DEMO_SCRIPT.md
│   ├── DEPLOYMENT.md
│   └── JUDGE_CHECKLIST.md
│
├── scripts/
│   ├── judge_smoke_test.py
│   ├── llm_probe.py
│   └── release_check.py
│
├── .github/workflows/ci.yml
├── render.yaml
└── README.md
```

---

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## Environment Configuration

Create a local `.env` from `.env.example`.

Example:

```env
INTERVAI_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
INTERVAI_LLM_API_KEY=YOUR_KEY
INTERVAI_LLM_MODEL=gemini-3.6-flash
INTERVAI_LLM_TIMEOUT_SECONDS=20
INTERVAI_LLM_MAX_RETRIES=1

INTERVAI_CORS_ORIGINS=http://localhost:5173
INTERVAI_SESSION_DB_PATH=
```

Frontend:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Never commit real API keys.

---

## Reliability & Validation

IntervAI includes:

- **72 backend automated tests**
- evaluator simulations across all supplied candidate profiles
- exact response-contract checks
- coverage checks
- adaptive-loop limits
- Pressure Mode limits
- session persistence tests
- malformed-model-output fallback tests
- Windows SQLite regression tests
- public deployment smoke-test script

Run:

```bash
cd backend
python -m pytest -q
```

Judge-style public API test:

```bash
python scripts/judge_smoke_test.py \
  --base-url https://intervai-f9nj.onrender.com
```

Provider test:

```bash
python scripts/llm_probe.py
```

Release validation:

```bash
python scripts/release_check.py \
  --base-url https://intervai-f9nj.onrender.com
```

---

## Live Deployment

**Application**

https://intervai.iitianpandit303.workers.dev/

**Backend**

https://intervai-f9nj.onrender.com

**Required evaluator endpoint**

```text
POST https://intervai-f9nj.onrender.com/api/interview
```

**Health**

https://intervai-f9nj.onrender.com/health

**Repository**

https://github.com/iitianpandit303-max/IntervAI

---

## Demo Flow

A useful demo sequence is:

1. Choose a candidate with mixed learning signals.
2. Start the interview.
3. Give a partially correct answer.
4. Show the immediate diagnostic probe.
5. Give a strong engineering answer.
6. Show a deeper or Pressure Mode challenge.
7. Point out the changing Candidate Knowledge Map.
8. Complete the interview.
9. Show the Interview Readiness Report and curriculum-day revision recommendations.

---

## Hackathon Requirement Coverage

| Requirement | IntervAI |
|---|---|
| Conversational multi-turn interview | ✅ |
| Minimum 8 questions | ✅ Deterministic guarantee |
| At least 4 curriculum days | ✅ Deterministic guarantee |
| Follow-ups based on previous answers | ✅ |
| Maintains interview context | ✅ |
| Structured feedback | ✅ |
| Required HTTP endpoint | ✅ |
| Candidate-profile personalization | ✅ |
| Actionable final preparation guidance | ✅ |
| Graceful LLM failure handling | ✅ |

---

## What makes IntervAI different?

IntervAI is not designed around “How many AI features can we add?”

It is designed around one question:

> **What would make an AI interview behave more like a thoughtful technical interviewer?**

That led to five core choices:

1. profile-aware questioning,
2. curriculum-grounded grading,
3. evidence-based adaptation,
4. engineering Pressure Mode,
5. deterministic constraints around probabilistic AI.

The model can be creative where creativity helps.  
The backend stays strict where reliability matters.

---

## License

Built for ViCodathon / ABTalks AI Interview Agent challenge.
