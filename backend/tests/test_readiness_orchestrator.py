from pathlib import Path
from typing import Any

from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_orchestrator import InterviewOrchestrator


TEST_DB = Path(__file__).resolve().parent / "test_readiness_sessions.db"


class ReportEvaluationLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "technical_accuracy": 3,
            "conceptual_understanding": 3,
            "engineering_reasoning": 3,
            "implementation_depth": 3,
            "communication_clarity": 4,
            "strong_points": ["Explained the main engineering decision clearly."],
            "missing_concepts": [],
            "misconceptions": [],
            "recommended_action": "SWITCH",
            "confidence": 0.9,
            "evaluator_rationale": "The answer is technically sound and clear enough to move on.",
        }


def _complete_session(session_id: str) -> tuple[InterviewOrchestrator, SessionRepository, object]:
    if TEST_DB.exists():
        TEST_DB.unlink()
    sessions = SessionRepository(TEST_DB)
    evaluator = AnswerEvaluator(llm=ReportEvaluationLLM())
    orchestrator = InterviewOrchestrator(sessions=sessions, answer_evaluator=evaluator)
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start(session_id, candidate)
    response = None
    for index in range(8):
        response = orchestrator.continue_interview(
            session_id,
            f"Candidate answer {index + 1} with a concrete engineering explanation.",
        )
    assert response is not None
    return orchestrator, sessions, response


def test_completion_persists_rich_readiness_report() -> None:
    _, sessions, response = _complete_session("readiness-persist")

    assert response.done is True
    stored = sessions.get("readiness-persist")
    assert stored is not None
    assert stored.final_report is not None
    assert stored.final_report.answered_questions == 8
    assert len(stored.final_report.curriculum_days_covered) >= 4
    assert stored.final_report.overall_score >= 70
    assert stored.final_report.communication_quality > 0

    if TEST_DB.exists():
        TEST_DB.unlink()


def test_repeated_completion_returns_same_stored_report() -> None:
    orchestrator, sessions, first_response = _complete_session("readiness-repeat")
    stored_before = sessions.get("readiness-repeat")
    assert stored_before is not None and stored_before.final_report is not None
    original = stored_before.final_report.model_dump()

    second_response = orchestrator.continue_interview("readiness-repeat", "ignored after completion")
    stored_after = sessions.get("readiness-repeat")

    assert second_response.done is True
    assert first_response.feedback == second_response.feedback
    assert stored_after is not None and stored_after.final_report is not None
    assert stored_after.final_report.model_dump() == original

    if TEST_DB.exists():
        TEST_DB.unlink()
