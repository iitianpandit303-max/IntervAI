from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_orchestrator import InterviewOrchestrator
import app.api.interview as interview_api


TEST_DB = Path(__file__).resolve().parent / "test_insights_sessions.db"


class StrongEvaluationLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "technical_accuracy": 4,
            "conceptual_understanding": 4,
            "engineering_reasoning": 4,
            "implementation_depth": 4,
            "communication_clarity": 4,
            "strong_points": ["Made a concrete engineering decision."],
            "missing_concepts": [],
            "misconceptions": [],
            "recommended_action": "SWITCH",
            "confidence": 0.95,
            "evaluator_rationale": "Strong curriculum-grounded answer.",
        }


def setup_module() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()
    interview_api.orchestrator = InterviewOrchestrator(
        sessions=SessionRepository(TEST_DB),
        answer_evaluator=AnswerEvaluator(llm=StrongEvaluationLLM()),
    )


def teardown_module() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_hidden_get_view_exposes_live_knowledge_map_without_changing_post_contract() -> None:
    client = TestClient(app)
    candidate = CandidateRepository().get("CAND-003")
    assert candidate is not None

    started = client.post(
        "/api/interview",
        json={"sessionId": "ui-live", "candidate": candidate.model_dump()},
    )
    assert started.status_code == 200
    assert set(started.json().keys()) == {"reply", "done"}

    view = client.get("/api/interview", params={"sessionId": "ui-live"})
    assert view.status_code == 200
    payload = view.json()
    assert payload["answeredQuestions"] == 0
    assert payload["knowledgeMap"]["candidate_id"] == "CAND-003"
    assert len(payload["knowledgeMap"]["topics"]) == 7
    assert payload["currentQuestion"] is not None

    client.post(
        "/api/interview",
        json={"sessionId": "ui-live", "message": "I would justify the design with measurable trade-offs."},
    )
    updated = client.get("/api/interview", params={"sessionId": "ui-live"}).json()
    assert updated["answeredQuestions"] == 1
    assert len(updated["curriculumDaysCovered"]) == 1


def test_completed_view_exposes_persisted_readiness_report() -> None:
    client = TestClient(app)
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    client.post(
        "/api/interview",
        json={"sessionId": "ui-complete", "candidate": candidate.model_dump()},
    )
    response = None
    for index in range(12):
        response = client.post(
            "/api/interview",
            json={
                "sessionId": "ui-complete",
                "message": f"Answer {index + 1} with a concrete implementation and trade-off.",
            },
        )
        if response.json()["done"]:
            break
    assert response is not None
    assert response.json()["done"] is True

    view = client.get("/api/interview", params={"sessionId": "ui-complete"})
    payload = view.json()
    assert payload["done"] is True
    assert payload["finalReport"] is not None
    assert payload["finalReport"]["answered_questions"] >= 8
    assert payload["currentQuestion"] is None


def test_unknown_insights_session_returns_404() -> None:
    client = TestClient(app)
    response = client.get("/api/interview", params={"sessionId": "not-here"})
    assert response.status_code == 404
