# IntervAI — AI Usage & Prompt Development Log

> **ViCodathon · Problem Statement 2 — The Interview Agent**

This document records how AI was used while building **IntervAI — Adaptive Technical Interview Engine** during the hackathon.

The project was **not generated in one large prompt**. It was built incrementally through architecture discussion, small implementation milestones, automated testing, debugging, deployment, and final documentation.

Short continuation prompts such as **“proceed”**, **“go on”**, or **“move on to commit 10”** were used inside an ongoing development context. For authenticity, this log records both the literal user prompt and the context carried from the previous milestone.

## Note on compilation and provenance

This file was compiled near the end of the hackathon from the ongoing ChatGPT development conversation.

Long product-definition prompts are reproduced directly where useful. Short continuation prompts such as `"proceed"` are shown together with the development context they continued.

The commit hashes below are checked against the public repository history. This log is intended to document the actual AI-assisted workflow, not to rewrite short prompts into more sophisticated prompts after the fact.

Where a development milestone does **not** appear as its own standalone commit in the current public history, this log says so explicitly instead of assigning an invented commit hash.


---

# 1. Initial Product Direction & Architecture

## User prompt

> I am choosing problem statement 2 which is the AI Interview Agent.
>
> I want to build an AI technical interviewer for the ABTalks AI Cohort. The main idea is that it should not feel like a normal chatbot which just asks fixed questions one by one. It should behave more like a real technical interviewer and change the interview depending on how the candidate answers.
>
> We will get curriculum JSON and candidate profile data, so first understand these properly and use them during the interview.
>
> Main requirements from the problem statement:
>
> * interview should be conversational and multi-turn
> * minimum 8 questions
> * questions should cover at least 4 different curriculum days
> * ask follow-up questions based on previous answers
> * remember context during the complete interview
> * give structured feedback at the end
> * expose the HTTP endpoint required in the technical specification
>
> I also want to add some extra features so it does not look like just another interview chatbot.
>
> One feature can be a Candidate Knowledge Map.
>
> During the interview maintain scores for areas like:
>
> RAG  
> Vector Databases  
> Prompt Engineering  
> Agentic AI  
> MCP  
> Deployment  
> Production AI Systems
>
> These scores should change depending on the answers of the candidate.
>
> For example if candidate gives a strong answer about RAG then we can go deeper instead of asking another basic definition question.
>
> If the answer is weak then ask a simpler diagnostic follow-up question to understand where exactly the candidate is confused.
>
> Questions should not only be definition based.
>
> Try to include different question types like:
>
> * concept questions
> * implementation questions
> * debugging situations
> * engineering trade-offs
> * system design
> * follow-up questions
>
> I also want something like a Pressure Mode.
>
> Sometimes the interviewer should challenge the candidate's answer.
>
> Example:
>
> Candidate says:
>
> "Vector databases are used to store embeddings and perform semantic search."
>
> Instead of saying correct and moving ahead, interviewer can ask:
>
> "PostgreSQL can also store vectors. Why would you choose a dedicated vector database instead?"
>
> This way the interview tests understanding and engineering decisions instead of memorized definitions.
>
> At the end generate an Interview Readiness Report.
>
> It can contain:
>
> * overall score
> * strongest topics
> * weakest topics
> * conceptual understanding
> * engineering reasoning
> * communication quality
> * answer depth
> * topics the candidate should revise
> * curriculum days they should revisit
> * questions where they struggled
> * suggested next preparation steps
>
> For now I do not want you to generate the whole project at once.
>
> First analyse the complete problem and design the architecture for this project.
>
> I am thinking of using:
>
> Frontend: React + Vite  
> Backend: FastAPI Python  
> AI: LLM API  
> Data: provided curriculum JSON + candidate profiles
>
> We do not need authentication or production user accounts unless required by the technical specification.
>
> Keep the project modular because if we qualify for the live steer challenge we may have to add a new feature within 20 minutes.
>
> For this first step only give me:
>
> 1. complete architecture
> 2. frontend and backend folder structure
> 3. main components/modules
> 4. interview flow
> 5. how interview memory/context should work
> 6. how adaptive question selection should work
> 7. how answer evaluation should work
> 8. how Candidate Knowledge Map should be updated
> 9. API flow
> 10. what data should be stored during one interview session
> 11. suggested development order so we can build and commit feature by feature
>
> Do not start writing the complete project code yet.
>
> Also keep things practical enough that we can actually finish and deploy this during the hackathon.

## AI-assisted design decisions

The architecture discussion established these project principles:

1. **LLM handles language and interpretation.**
2. **Deterministic backend policy guarantees the hackathon contract.**
3. Candidate history creates an interview prior, but live answers can override it.
4. Adaptive follow-ups are inserted without sacrificing curriculum coverage.
5. The interview remains bounded rather than allowing unlimited follow-up chains.
6. The curriculum is small and structured enough that a vector database is unnecessary for v1.
7. The project should be modular enough for the Live Steer Challenge.

## Resulting implementation

These ideas became:

- `CandidateAnalyzer`
- `InterviewPlanner`
- `CoveragePolicy`
- structured `AnswerEvaluator`
- adaptive `RECOVER / PROBE / DEEPEN / SWITCH`
- Pressure Mode
- Candidate Knowledge Map
- structured interview memory
- Interview Readiness Report

This initial prompt maps directly to most of the final product's differentiating features.

---

# 2. Key Commit-by-Commit AI-Assisted Build Trace

The implementation hashes below are from the public `master` branch. Final documentation-only commits (README polish, screenshots, and this prompt log) are intentionally omitted from the implementation trace.

---

## Commit `0976949`
### `chore: initialize React and FastAPI project structure`

### User prompt

> Ok, Then we will proceed with commit 1-3.

### Context / goal

Start with a minimal, testable foundation rather than generating the full product at once.

### AI-assisted implementation

- React + Vite frontend skeleton
- FastAPI backend skeleton
- health route
- repository structure
- environment examples
- documentation foundation

### Why this mattered

It ensured the first commit was only infrastructure rather than a nearly complete imported application.

---

## Commit `9b97202`
### `feat: load and validate curriculum and candidate profiles`

### Prompt context

Same Commit 1–3 request, second milestone.

### AI-assisted implementation

- load supplied 31-day curriculum JSON
- load supplied candidate profile JSON
- Pydantic validation
- curriculum lookup/indexing
- candidate repository
- day-number-based candidate-to-curriculum joining

### Important engineering decision

Candidate missions were matched by **day number**, not title text, because titles can differ slightly between candidate data and curriculum data.

---

## Commit `cceb925`
### `feat: implement interview API contract and session lifecycle`

### Prompt context

Same Commit 1–3 request, third milestone.

### AI-assisted implementation

- required `/api/interview` flow
- session lifecycle using `sessionId`
- mock questions before LLM integration
- SQLite-backed session state
- required completion feedback structure

### Important engineering decision

The evaluator API contract was implemented **before** AI integration so later model work could not destabilize the required interface.

---

## Commit `9583899`
### `feat: derive interview signals from candidate learning history`

### Literal user prompt

> then lets proceed

### Context carried from previous turn

Build **Commit 4 — Candidate Intelligence** using passed, failed, skipped, attempts, commit activity, role, and experience.

### AI-assisted implementation

Candidate history was transformed into signals such as:

- `STRONG`
- `DEVELOPING`
- `DIAGNOSTIC`
- `FAILED`
- `SKIPPED`
- `UNKNOWN`

Derived interview metadata included:

- starting difficulty
- profile confidence
- strong days
- diagnostic days
- failed/skipped days
- interview priority days

### Important engineering decision

**Missing mission data is UNKNOWN, not FAILED.**

Sparse candidate records should not create false negative evidence.

---

## Commit `63558df`
### `feat: add curriculum-aware interview planning and coverage rules`

### Literal user prompt

> yes we ready to proceed further

### Context carried from previous turn

Build Commit 5: personalized interview planning plus deterministic minimum coverage.

### AI-assisted implementation

- minimum 8 planned questions
- minimum 4 curriculum days
- curriculum-aware topic prioritization
- question-type rotation:
  - concept
  - implementation
  - debugging
  - trade-off
  - system design

### Important engineering decision

Hard requirements are enforced by code rather than asking the LLM to “remember” them.

---

## Commit `9aab2b0`
### `feat: integrate structured LLM question generation`

### Literal user prompt

> ok lets proceed further with commit 6

### Context / goal

Add the first real LLM layer without surrendering deterministic interview control.

### AI-assisted implementation

The planner chooses:

- curriculum day
- question type
- difficulty
- purpose

The LLM converts that structured slot into natural interviewer language.

### Reliability design

If the provider:

- is unavailable
- times out
- returns malformed JSON
- fails schema validation

IntervAI keeps the deterministic fallback question and continues.

### Why this mattered

The LLM enriches the interview but is not a single point of failure.

---

## Windows SQLite Debugging

### User-provided failure

> `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`

The failure appeared during test cleanup of a SQLite database.

### AI-assisted diagnosis

The code used SQLite context management that committed/rolled back but did not always explicitly close the underlying connection before Windows attempted to delete the test DB.

### Fix

Explicitly close every SQLite connection.

### Result

The same test suite became portable on the user's Windows development machine.

---

## Commit `345ddd4`
### `feat: add curriculum-grounded answer evaluation`

### Literal user prompt

> proceed

### Context carried from previous turn

Build Commit 7 — understand candidate answers but do not yet alter the interview flow.

### AI-assisted rubric

Every answer produces structured scores for:

- technical accuracy
- conceptual understanding
- engineering reasoning
- implementation depth
- communication clarity

and structured evidence:

- strong points
- missing concepts
- misconceptions
- recommended next action
- evaluation confidence

### Important engineering decision

Fallback evaluation uses:

```text
confidence = 0
```

so provider failures cannot later become fake mastery evidence.

---

## Commit `a58143d`
### `feat: adapt interview flow from answer evaluations`

### Literal user prompt

> proceed further

### Context carried from previous turn

Use Commit 7's answer signals to create true adaptive behavior.

### AI-assisted implementation

Actions:

- `RECOVER`
- `PROBE`
- `DEEPEN`
- `SWITCH`

### Important engineering decision

Adaptive questions are **inserted** into the interview rather than replacing the original planned questions.

This protects the deterministic 8-question / 4-day coverage requirements.

### Bounded adaptation

Adaptive follow-ups have a strict budget so the interview cannot loop indefinitely.

---

## Commit `cdc9e7b`
### `feat: add pressure mode for engineering trade-offs`

### Literal user prompt

> proceed further

### Context carried from previous turn

Implement the user's original **Pressure Mode** concept separately from normal adaptation.

### AI-assisted Pressure strategies

- challenge an assumption
- introduce an alternative
- create a counterfactual
- change an engineering constraint

### Eligibility logic

Pressure is only appropriate when the prior answer has strong technical evidence and sufficient evaluation confidence.

Weak candidates receive diagnostic support rather than artificial pressure.

### Example product behavior

Candidate:

> “I would use Pinecone because we want managed scaling.”

IntervAI:

> “If the dataset fits comfortably on one machine and PostgreSQL already exists in the stack, why introduce another managed service?”

---

## Knowledge Map development milestone
### No standalone public commit assigned

### Literal user prompt

> ok move on to commit 10

### Public-history note

The Knowledge Map was developed as its own implementation milestone in the AI-assisted workflow, but the current public `master` history shown during final verification does **not** contain a separate commit titled `feat: track dynamic candidate mastery across AI domains`.

For authenticity, this log therefore does not invent or reuse a hash for that milestone. The Knowledge Map code is present in the integrated project and is exercised by the later memory, readiness-report, and visualization milestones.

### Context / goal

Create an evidence-backed Candidate Knowledge Map for:

- RAG
- Vector Databases
- Prompt Engineering
- Agentic AI
- MCP
- Deployment
- Production AI Systems

### Scoring design

Live technical evidence updates mastery with weighting based on:

- answer quality
- evaluator confidence
- question difficulty
- question type

### Important decision

Communication quality does **not** directly lower technical mastery. It is evaluated separately in the final readiness report.

---

## Commit `2c700d9`
### `feat: add structured interview memory and context management`

### Literal user prompt

> ok move on with commit 11

### Context / goal

Maintain context without sending the complete transcript back to the model every turn.

### AI-assisted memory architecture

```text
Full transcript → persisted in SQLite

Working memory → sent to the LLM
  - recent turns
  - known strengths
  - open gaps
  - misconceptions
  - curriculum context
  - Knowledge Map snapshot
  - deterministic rolling summary
```

### Important decision

Memory summarization is deterministic instead of adding another LLM request after every answer.

This reduces cost and latency.

---

## Commit `56a7677`
### `feat: generate structured interview readiness report`

### Literal user prompt

> done proceed

### Context / goal

Use all accumulated evidence to generate the final Interview Readiness Report.

### AI-assisted report structure

- overall score
- readiness level
- evidence confidence
- technical accuracy
- conceptual understanding
- engineering reasoning
- communication quality
- answer depth
- strongest topics
- weakest topics
- topics to revise
- curriculum days to revisit
- struggled questions
- next preparation steps

### API compatibility decision

Internally IntervAI keeps a rich report, while externally it maps to the required evaluator schema:

```json
{
  "summary": "...",
  "strengths": [],
  "gaps": [],
  "next": []
}
```

---

## Commit `2618682`
### `feat: build conversational React interview room`

### Literal user prompt

> go on

### Context / goal

Turn the backend engine into a usable product demo.

### AI-assisted implementation

- candidate selection
- live conversational interview
- answer composer
- progress
- loading states
- errors
- curriculum-day metadata
- adaptive interview state

### UI philosophy

Keep the frontend dependency-light so a live feature request can be implemented quickly during the Live Steer Challenge.

---

## Commit `e019da9`
### `feat: visualize knowledge map and interview readiness report`

### Literal user prompt

> ready

### Context / goal

Expose the intelligence already stored in backend state.

### AI-assisted implementation

- live Knowledge Map
- evidence-backed mastery scores
- final overall score
- rubric dimensions
- strongest/weakest areas
- curriculum revisit days
- Pressure Mode stats
- struggled questions
- next preparation steps

### Result

The project became visually demonstrable rather than requiring judges to inspect raw API state.

---

## Commit `7e1b381`
### `chore: harden evaluator flow and deployment reliability`

### Literal user prompt

> done proceed further

### Context / goal

Stop adding flashy features and judge-proof the application.

### AI-assisted reliability work

- stricter API contract validation
- malformed-request rejection
- bounded transient retries
- timeout fallback
- configurable CORS
- evaluator smoke-test script
- supplied-candidate simulations
- deployment checks

### Engineering principle

A hackathon project should degrade gracefully rather than fail completely when an external model API is unreliable.

---

## Commit `0a88f63`
### `chore: prepare production release and submission package`

### Literal user prompt

> done continue with commit 16

### Context / goal

Prepare for actual deployment and final submission.

### AI-assisted implementation

- environment-configurable session DB path
- LLM probe
- one-command release checker
- Docker support
- GitHub Actions
- deployment documentation
- judge checklist
- demo script
- submission template

---

## Commit `022b3a6`
### `fix: support latest Gemini 3.6 Flash API`

### Deployment debugging context

The original Gemini model configuration returned:

> `gemini-2.5-flash is no longer available to new users`

### AI-assisted diagnosis

The API key was valid; the requested model was no longer available for new users.

### Fix

- migrate deployment model to `gemini-3.6-flash`
- remove deprecated sampling configuration from the shared LLM client

### Result

Structured LLM probing and live interviewer generation worked again.

---

# 3. Deployment Debugging Trace

AI assistance continued during deployment rather than ending after code generation.

---

## Render — Python Version Failure

### User supplied log

> `Using Python version 3.14.3 (default)`

followed by:

> `pydantic-core`
>
> `maturin failed`
>
> `Read-only file system`

### AI-assisted diagnosis

The project had been developed/tested on Python 3.12, while Render defaulted to Python 3.14. The pinned Pydantic stack did not have the expected prebuilt path for that environment and attempted a Rust build.

### Fix

```text
PYTHON_VERSION=3.12.0
```

### Verification

The next Render log showed:

> `Using Python version 3.12.0 via environment variable PYTHON_VERSION`

---

## Render — Monorepo Root Failure

### User supplied log

> `ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'`

### AI-assisted diagnosis

Render was executing from the repository root, while the backend lived under `backend/`.

### Fix

```text
Root Directory = backend
Build Command = pip install -r requirements.txt
Start Command = uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Result

The Render service deployed and `/health` returned HTTP 200.

---

## Public Backend URL Debugging

### Observed issue

A manually typed Render hostname returned HTTP 404 even though Render's health check was passing.

### AI-assisted debugging step

Copy the exact primary Render URL from the service instead of typing it from memory.

### Result

The correct public URL returned:

```text
status = ok
version = 0.6.0
llmMode = configured
```

and FastAPI `/docs` loaded successfully.

---

## Cloudflare — Monorepo Build Failure

### User supplied log

> `Could not read package.json`
>
> `/opt/buildhome/repo/package.json`

### AI-assisted diagnosis

The frontend package was under `frontend/`, but Cloudflare was building from repository root.

### Fix

```text
Root directory = frontend
Build command = npm run build
```

### Result

Vite built the production bundle successfully.

---

## Cloudflare — Wrangler Auto-Configuration Failure

### User supplied log

> `Cannot modify Vite config: could not find a valid plugins array.`

### AI-assisted diagnosis

Plain `wrangler deploy` was attempting to modify/configure the Vite project rather than simply upload the already-built static assets.

### Fix

Deploy the Vite `dist` directory directly:

```text
npx wrangler deploy --assets ./dist --name intervai
```

---

## Cloudflare — Compatibility Date Failure

### User supplied log

> `A compatibility_date is required when uploading a Worker.`

### Fix

```text
npx wrangler deploy --assets ./dist --name intervai --compatibility-date 2026-08-08
```

### Result

Cloudflare Worker static deployment succeeded.

---

## Frontend → Backend CORS Failure

### User report

> well it failed to fetch i think we need to run backend in another powershell

### AI-assisted diagnosis

No local backend was needed anymore. The public Cloudflare frontend needed permission to call the public Render API.

### Fix

Render configuration:

```text
INTERVAI_CORS_ORIGINS=http://localhost:5173,https://intervai.iitianpandit303.workers.dev
```

### Result

The public frontend successfully called the Render backend and completed a live interview.

---

# 4. Final End-to-End Validation

The live system was manually exercised through:

```text
Cloudflare frontend
      ↓
Render FastAPI
      ↓
Gemini
      ↓
question generation
      ↓
candidate answer
      ↓
structured evaluation
      ↓
adaptive / pressure behavior
      ↓
Knowledge Map
      ↓
final Readiness Report
```

A manual live interview completed after 10 answered questions, including adaptive questions, and produced the final readiness report.

The public backend smoke-test tooling was also used against the deployed API.

---

# 5. Prompt-to-Feature Traceability Summary

| Human direction | Implemented feature |
|---|---|
| “should not feel like a normal chatbot” | Adaptive stateful interviewer |
| “change the interview depending on how candidate answers” | RECOVER / PROBE / DEEPEN / SWITCH |
| “Candidate Knowledge Map” | Seven-domain live mastery model |
| “strong answer about RAG then go deeper” | DEEPEN policy |
| “weak answer then simpler diagnostic follow-up” | RECOVER / PROBE |
| “implementation, debugging, trade-offs, system design” | Question-type planner |
| “Pressure Mode” | Evidence-triggered engineering challenge strategy |
| “PostgreSQL can also store vectors...” | Alternative/assumption pressure questions |
| “Interview Readiness Report” | Rich final evidence report |
| “minimum 8 questions” | Deterministic coverage policy |
| “at least 4 curriculum days” | Deterministic curriculum coverage |
| “remember context” | Structured working memory |
| “keep project modular for 20 minute live steer” | Separate services / strategies / prompts / UI components |
| “do not generate whole project at once” | Incremental feature commits |

---

# 6. How AI Was Used

AI was used for:

- architecture exploration
- code generation
- code review
- test design
- debugging from real logs
- API integration
- deployment troubleshooting
- documentation
- README/submission preparation

AI was **not** given unrestricted authority over product behavior.

The core design intentionally divides responsibilities.

## LLM responsibilities

- natural interviewer wording
- answer interpretation
- misconception extraction
- follow-up wording
- engineering challenges

## Deterministic application responsibilities

- evaluator API schema
- session lifecycle
- minimum 8 questions
- minimum 4 curriculum days
- question limits
- adaptive follow-up budget
- Pressure Mode budget
- curriculum selection
- persistence
- schema validation
- completion conditions
- fallback behavior

---

# 7. Development Method

The AI-assisted workflow used throughout the hackathon was:

```text
Human product direction
        ↓
AI-assisted design discussion
        ↓
Small implementation milestone
        ↓
Automated tests
        ↓
Manual verification
        ↓
Git commit
        ↓
Next feature
        ↓
Real deployment logs
        ↓
AI-assisted debugging
        ↓
Production verification
```

This is why the public repository contains a progressive commit history instead of one final generated code dump.

---

# 8. Public Project Links

**Repository**

https://github.com/iitianpandit303-max/IntervAI

**Live application**

https://intervai.iitianpandit303.workers.dev/

**Backend API**

https://intervai-f9nj.onrender.com

**Required evaluator endpoint**

```text
POST https://intervai-f9nj.onrender.com/api/interview
```

**API docs**

https://intervai-f9nj.onrender.com/docs
