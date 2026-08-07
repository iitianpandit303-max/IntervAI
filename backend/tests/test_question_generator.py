from typing import Any

from app.models.session import QuestionGenerationSource
from app.repositories.candidate_repository import CandidateRepository
from app.services.interview_planner import InterviewPlanner
from app.services.question_generator import QuestionGenerator


class FakeLLM:
    def __init__(self, payload: dict[str, Any] | None = None, enabled: bool = True) -> None:
        self.payload = payload or {}
        self._enabled = enabled
        self.calls = 0
        self.last_user_prompt = ""

    @property
    def enabled(self) -> bool:
        return self._enabled

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.calls += 1
        self.last_user_prompt = user_prompt
        return self.payload


def _planned_question():
    candidate = CandidateRepository().get("CAND-002")
    assert candidate is not None
    return candidate, InterviewPlanner().build_plan(candidate)[0]


def test_valid_llm_question_replaces_deterministic_wording() -> None:
    candidate, planned = _planned_question()
    fake = FakeLLM(
        {
            "question": "Your retrieval results are semantically close but still miss the user's intent. What would you inspect first, and why?",
            "rationale": "Tests practical reasoning against the selected curriculum objective.",
        }
    )

    result = QuestionGenerator(llm=fake).materialize(candidate=candidate, planned=planned)

    assert result.generation_source == QuestionGenerationSource.LLM
    assert result.text.startswith("Your retrieval results")
    assert fake.calls == 1
    assert candidate.member.jobRole in fake.last_user_prompt
    assert planned.source_objective in fake.last_user_prompt


def test_disabled_llm_keeps_safe_deterministic_question() -> None:
    candidate, planned = _planned_question()
    fake = FakeLLM(enabled=False)

    result = QuestionGenerator(llm=fake).materialize(candidate=candidate, planned=planned)

    assert result.text == planned.text
    assert result.generation_source == QuestionGenerationSource.FALLBACK
    assert fake.calls == 0


def test_malformed_llm_payload_falls_back_instead_of_breaking_session() -> None:
    candidate, planned = _planned_question()
    fake = FakeLLM({"question": "too short", "rationale": "x"})

    result = QuestionGenerator(llm=fake).materialize(candidate=candidate, planned=planned)

    assert result.text == planned.text
    assert result.generation_source == QuestionGenerationSource.FALLBACK


def test_materialized_question_is_idempotent() -> None:
    candidate, planned = _planned_question()
    fake = FakeLLM(
        {
            "question": "How would you verify that your retrieval approach is returning the right evidence before blaming the language model?",
            "rationale": "Grounded debugging question.",
        }
    )
    generator = QuestionGenerator(llm=fake)

    first = generator.materialize(candidate=candidate, planned=planned)
    second = generator.materialize(candidate=candidate, planned=first)

    assert first == second
    assert fake.calls == 1
