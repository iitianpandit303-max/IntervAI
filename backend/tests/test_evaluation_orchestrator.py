from pathlib import Path
from typing import Any

from app.models.answer_evaluation import EvaluationSource, RecommendedAction
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_orchestrator import InterviewOrchestrator


TEST_DB = Path(__file__).resolve().parent / "test_evaluation_sessions.db"


class EvaluationFakeLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "technical_accuracy": 3,
            "conceptual_understanding": 3,
            "engineering_reasoning": 2,
            "implementation_depth": 2,
            "communication_clarity": 4,
            "strong_points": ["Explained the core idea clearly."],
            "missing_concepts": ["Needs more implementation detail."],
            "misconceptions": [],
            "recommended_action": "PROBE",
            "confidence": 0.88,
            "evaluator_rationale": "The response is correct but leaves a useful implementation gap to probe.",
        }


def test_orchestrator_persists_evaluation_and_uses_it_for_adaptation() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()

    sessions = SessionRepository(TEST_DB)
    evaluator = AnswerEvaluator(llm=EvaluationFakeLLM())
    orchestrator = InterviewOrchestrator(sessions=sessions, answer_evaluator=evaluator)
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start("evaluation-session", candidate)
    before = sessions.get("evaluation-session")
    assert before is not None
    original_question_count = len(before.questions)

    response = orchestrator.continue_interview(
        "evaluation-session",
        "The main idea is to retrieve relevant evidence first and ground generation in that evidence.",
    )

    assert response.done is False
    stored = sessions.get("evaluation-session")
    assert stored is not None
    assert len(stored.turns) == 1
    assert stored.turns[0].evaluation is not None
    assert stored.turns[0].evaluation.source is EvaluationSource.LLM
    assert stored.turns[0].evaluation.recommended_action is RecommendedAction.PROBE
    assert len(stored.questions) == original_question_count + 1
    assert stored.questions[1].adaptive_action is RecommendedAction.PROBE

    if TEST_DB.exists():
        TEST_DB.unlink()
