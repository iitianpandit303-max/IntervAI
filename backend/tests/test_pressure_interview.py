from pathlib import Path
from typing import Any

from app.models.answer_evaluation import RecommendedAction
from app.models.interview_plan import QuestionType
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_orchestrator import InterviewOrchestrator
from app.services.pressure_question_generator import PressureQuestionGenerator


TEST_DB = Path(__file__).resolve().parent / "test_pressure_sessions.db"


class StrongPressureEvaluationLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "technical_accuracy": 4,
            "conceptual_understanding": 4,
            "engineering_reasoning": 4,
            "implementation_depth": 3,
            "communication_clarity": 4,
            "strong_points": ["Makes and justifies a concrete engineering choice."],
            "missing_concepts": [],
            "misconceptions": [],
            "recommended_action": "PRESSURE",
            "confidence": 0.95,
            "evaluator_rationale": "The answer is strong and includes a decision worth challenging.",
        }


class PressureQuestionLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        assert "Pressure challenge type:" in user_prompt
        return {
            "question": (
                "You defended that approach. Now assume the cheaper alternative meets today's load; "
                "what evidence would justify keeping your more complex design?"
            ),
            "rationale": "Forces the candidate to defend the decision under a credible alternative.",
        }


def cleanup() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_pressure_challenge_is_inserted_without_replacing_coverage_plan() -> None:
    cleanup()
    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        answer_evaluator=AnswerEvaluator(llm=StrongPressureEvaluationLLM()),
        pressure_question_generator=PressureQuestionGenerator(llm=PressureQuestionLLM()),
    )
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start("pressure-one", candidate)
    before = sessions.get("pressure-one")
    assert before is not None
    original_plan_ids = [q.question_id for q in before.questions]

    response = orchestrator.continue_interview(
        "pressure-one",
        "I would choose this architecture because it gives us managed scaling and simpler operations.",
    )
    assert response.done is False
    assert "what evidence" in response.reply.lower()

    stored = sessions.get("pressure-one")
    assert stored is not None
    assert stored.adaptive_followups_used == 1
    assert stored.pressure_followups_used == 1
    pressure = stored.questions[1]
    assert pressure.question_type is QuestionType.PRESSURE
    assert pressure.adaptive_action is RecommendedAction.PRESSURE
    assert pressure.adaptive_from_question_id == stored.questions[0].question_id
    assert [q.question_id for q in stored.questions if q.adaptive_from_question_id is None] == original_plan_ids
    cleanup()


def test_pressure_question_does_not_chain_and_total_interview_stays_bounded() -> None:
    cleanup()
    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        answer_evaluator=AnswerEvaluator(llm=StrongPressureEvaluationLLM()),
        pressure_question_generator=PressureQuestionGenerator(llm=PressureQuestionLLM()),
    )
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start("pressure-bounded", candidate)
    response = None
    for index in range(10):
        response = orchestrator.continue_interview(
            "pressure-bounded",
            f"Strong engineering answer {index + 1} with a defended implementation choice.",
        )

    assert response is not None
    assert response.done is True
    assert response.feedback is not None
    assert "10 answered questions" in response.feedback.summary
    assert "2 pressure challenge(s)" in response.feedback.summary

    stored = sessions.get("pressure-bounded")
    assert stored is not None
    assert stored.adaptive_followups_used == 2
    assert stored.pressure_followups_used == 2
    assert sum(q.question_type is QuestionType.PRESSURE for q in stored.questions) == 2

    answered_ids = {turn.question_id for turn in stored.turns}
    answered_days = {q.day for q in stored.questions if q.question_id in answered_ids}
    assert len(answered_days) >= 4
    cleanup()
