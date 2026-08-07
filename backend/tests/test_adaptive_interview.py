from pathlib import Path
from typing import Any

from app.models.answer_evaluation import EvaluationSource, RecommendedAction
from app.models.session import QuestionGenerationSource
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.adaptive_question_generator import AdaptiveQuestionGenerator
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_orchestrator import InterviewOrchestrator


TEST_DB = Path(__file__).resolve().parent / "test_adaptive_sessions.db"


class ProbeEvaluationLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "technical_accuracy": 2,
            "conceptual_understanding": 2,
            "engineering_reasoning": 2,
            "implementation_depth": 1,
            "communication_clarity": 3,
            "strong_points": ["Understands semantic retrieval."],
            "missing_concepts": ["metadata filtering"],
            "misconceptions": [],
            "recommended_action": "PROBE",
            "confidence": 0.92,
            "evaluator_rationale": "The answer is partially correct but omits metadata filtering.",
        }


class AdaptiveQuestionLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        assert "metadata filtering" in user_prompt
        assert "Adaptive action: PROBE" in user_prompt
        return {
            "question": "You covered semantic retrieval; how would metadata filtering prevent semantically similar results from the wrong plan from being returned?",
            "rationale": "The follow-up targets the concrete missing concept from the previous answer.",
        }


def test_probe_is_inserted_immediately_without_replacing_original_coverage_plan() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()

    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        answer_evaluator=AnswerEvaluator(llm=ProbeEvaluationLLM()),
        adaptive_question_generator=AdaptiveQuestionGenerator(llm=AdaptiveQuestionLLM()),
    )
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start("adaptive-probe", candidate)
    before = sessions.get("adaptive-probe")
    assert before is not None
    original_plan_days = [question.day for question in before.questions]
    first_day = before.questions[0].day

    response = orchestrator.continue_interview(
        "adaptive-probe",
        "I would use semantic similarity to retrieve the closest chunks.",
    )
    assert response.done is False
    assert "metadata filtering" in response.reply.lower()

    stored = sessions.get("adaptive-probe")
    assert stored is not None
    assert len(stored.questions) == 9
    assert stored.adaptive_followups_used == 1
    assert stored.questions[1].day == first_day
    assert stored.questions[1].adaptive_action is RecommendedAction.PROBE
    assert stored.questions[1].adaptive_from_question_id == stored.questions[0].question_id
    assert stored.questions[1].generation_source is QuestionGenerationSource.LLM

    # The original deterministic eight-question coverage plan is still present,
    # merely shifted one slot by the inserted follow-up.
    assert [question.day for question in stored.questions if question.adaptive_from_question_id is None] == original_plan_days

    if TEST_DB.exists():
        TEST_DB.unlink()


def test_adaptive_followup_does_not_chain_another_followup() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()

    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        answer_evaluator=AnswerEvaluator(llm=ProbeEvaluationLLM()),
        adaptive_question_generator=AdaptiveQuestionGenerator(llm=AdaptiveQuestionLLM()),
    )
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start("no-chain", candidate)
    orchestrator.continue_interview("no-chain", "Partial first answer")
    stored = sessions.get("no-chain")
    assert stored is not None
    assert stored.adaptive_followups_used == 1

    # This evaluates the adaptive question with the same PROBE signal. Policy
    # must return to the preserved plan rather than create an endless probe chain.
    orchestrator.continue_interview("no-chain", "Partial follow-up answer")
    stored = sessions.get("no-chain")
    assert stored is not None
    assert stored.adaptive_followups_used == 1
    assert stored.current_index == 2
    assert stored.questions[2].adaptive_from_question_id is None

    if TEST_DB.exists():
        TEST_DB.unlink()


def test_bounded_adaptation_completes_with_ten_questions_and_keeps_four_day_minimum() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()

    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        answer_evaluator=AnswerEvaluator(llm=ProbeEvaluationLLM()),
        adaptive_question_generator=AdaptiveQuestionGenerator(llm=AdaptiveQuestionLLM()),
    )
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start("bounded-adaptive", candidate)
    response = None
    for index in range(10):
        response = orchestrator.continue_interview(
            "bounded-adaptive",
            f"Candidate answer {index + 1}",
        )

    assert response is not None
    assert response.done is True
    assert response.feedback is not None
    assert "10 answered questions" in response.feedback.summary

    stored = sessions.get("bounded-adaptive")
    assert stored is not None
    assert stored.done is True
    assert stored.adaptive_followups_used == 2
    answered_ids = {turn.question_id for turn in stored.turns}
    answered_days = {
        question.day for question in stored.questions if question.question_id in answered_ids
    }
    assert len(answered_days) >= 4

    if TEST_DB.exists():
        TEST_DB.unlink()
