from typing import Any

from app.models.answer_evaluation import EvaluationSource, RecommendedAction
from app.repositories.candidate_repository import CandidateRepository
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_planner import InterviewPlanner


class FakeLLM:
    def __init__(self, payload: dict[str, Any] | None = None, enabled: bool = True) -> None:
        self.payload = payload or {}
        self._enabled = enabled
        self.calls = 0
        self.last_system_prompt = ""
        self.last_user_prompt = ""

    @property
    def enabled(self) -> bool:
        return self._enabled

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.calls += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.payload


def _context():
    candidate = CandidateRepository().get("CAND-002")
    assert candidate is not None
    question = InterviewPlanner().build_plan(candidate)[0]
    return candidate, question


def _strong_payload() -> dict[str, Any]:
    return {
        "technical_accuracy": 4,
        "conceptual_understanding": 4,
        "engineering_reasoning": 3,
        "implementation_depth": 3,
        "communication_clarity": 4,
        "strong_points": ["Connected the design choice to retrieval quality."],
        "missing_concepts": ["Could discuss measurement strategy in more detail."],
        "misconceptions": [],
        "recommended_action": "DEEPEN",
        "confidence": 0.91,
        "evaluator_rationale": "The answer is technically sound and supports a deeper follow-up.",
    }


def test_valid_evaluation_is_curriculum_grounded_and_structured() -> None:
    candidate, question = _context()
    fake = FakeLLM(_strong_payload())

    result = AnswerEvaluator(llm=fake).evaluate(
        candidate=candidate,
        question=question,
        answer="I would first define a measurable retrieval baseline and inspect the evidence returned for representative queries.",
    )

    assert result.source is EvaluationSource.LLM
    assert result.technical_accuracy == 4
    assert result.recommended_action is RecommendedAction.DEEPEN
    assert result.average_score == 3.6
    assert fake.calls == 1
    assert question.source_objective in fake.last_user_prompt
    assert question.text in fake.last_user_prompt
    assert "measurable retrieval baseline" in fake.last_user_prompt
    assert "0 = missing" in fake.last_system_prompt


def test_invalid_evaluation_falls_back_without_breaking_session_state() -> None:
    candidate, question = _context()
    fake = FakeLLM({"technical_accuracy": 99})

    result = AnswerEvaluator(llm=fake).evaluate(
        candidate=candidate,
        question=question,
        answer="A candidate answer that should still leave the interview usable.",
    )

    assert result.source is EvaluationSource.FALLBACK
    assert result.confidence == 0.0
    assert result.average_score == 2.0
    assert result.recommended_action is RecommendedAction.SWITCH


def test_disabled_llm_uses_zero_confidence_neutral_fallback() -> None:
    candidate, question = _context()
    fake = FakeLLM(enabled=False)

    result = AnswerEvaluator(llm=fake).evaluate(
        candidate=candidate,
        question=question,
        answer="A substantive answer.",
    )

    assert fake.calls == 0
    assert result.source is EvaluationSource.FALLBACK
    assert result.confidence == 0.0
    assert result.average_score == 2.0


def test_empty_answer_is_rule_scored_as_recovery_case() -> None:
    candidate, question = _context()
    fake = FakeLLM(_strong_payload())

    result = AnswerEvaluator(llm=fake).evaluate(
        candidate=candidate,
        question=question,
        answer="   ",
    )

    assert fake.calls == 0
    assert result.source is EvaluationSource.RULE
    assert result.average_score == 0.0
    assert result.recommended_action is RecommendedAction.RECOVER
    assert result.missing_concepts == ["No substantive answer was provided."]
