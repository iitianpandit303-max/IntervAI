# AI Workflow and Prompt Strategy

IntervAI uses AI for language understanding and generation, while deterministic backend policy owns hackathon constraints and session safety.

## What the LLM is allowed to do

The LLM is used to:

- turn a curriculum-grounded plan slot into a natural interview question;
- evaluate a candidate answer against the selected curriculum day and objective;
- phrase targeted RECOVER / PROBE / DEEPEN follow-ups;
- phrase Pressure Mode challenges for strong answers.

The model is **not** trusted to decide whether the interview satisfies the minimum requirements. Backend policy owns question count, curriculum-day coverage, adaptive budgets, session state, completion, and final response shape.

## Prompt layers

Prompt templates live in `backend/app/prompts/`:

- `interviewer.md` — natural planned questions;
- `evaluator.md` — rubric-based answer evaluation;
- `adaptive_interviewer.md` — diagnostic or deeper same-day follow-ups;
- `pressure_interviewer.md` — professional assumption/trade-off challenges;
- `feedback.md` — retained as documentation for report wording, while final aggregation is deterministic.

Each prompt receives only the context needed for its task: candidate background, curriculum day/objectives/tools, question metadata, and bounded working memory. This avoids dumping the entire transcript into every request.

## Structured output

LLM outputs are parsed as JSON and validated with Pydantic before entering interview state. Invalid, timed-out, or unavailable model responses fall back to deterministic behavior. Fallback answer evaluations have `confidence=0`, so provider failures cannot fabricate mastery or readiness evidence.

## Why no vector database

The supplied curriculum contains only 31 structured days and already provides day numbers, modules, tools, and objectives. Direct indexed lookup is simpler, faster, and more deterministic than adding a vector database solely for curriculum retrieval.

## Why the design is live-steer friendly

Interview planning, evaluation, adaptive policy, Pressure Mode, Knowledge Map, memory, and feedback are separate modules. A new interview behavior can be added or disabled without rewriting the evaluator endpoint or the rest of the system.
