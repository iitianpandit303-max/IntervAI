# IntervAI Demo Script

## 90-second demo

1. **Open the candidate selector.**
   - Explain that candidates have different completion, attempt, skip, failure, role, and experience signals.
   - Pick a candidate with an interesting learning history.

2. **Start the interview.**
   - Point out that the first question is grounded in that candidate's completed curriculum.
   - Mention the deterministic guarantee: at least 8 questions across at least 4 curriculum days.

3. **Give a deliberately partial answer.**
   - Show that IntervAI probes the missing concept instead of moving to an unrelated fixed question.

4. **Give a strong engineering answer later.**
   - Show Pressure Mode challenging an assumption or trade-off.

5. **Point at the live Knowledge Map.**
   - Scores change from low-confidence profile priors toward evidence from actual interview answers.

6. **Finish the interview.**
   - Show overall readiness, rubric scores, strongest/weakest topics, struggled questions, curriculum days to revisit, and next preparation steps.

## Architecture line for judges

> IntervAI is a deterministic interview state machine wrapped around an LLM: code guarantees coverage and API correctness; the model handles natural language, answer understanding, and contextual follow-ups.

## If the model provider fails during the demo

Continue the interview. IntervAI falls back to deterministic curriculum-grounded questions and keeps the API/session contract alive. Mention this as an intentional reliability feature rather than hiding it.
