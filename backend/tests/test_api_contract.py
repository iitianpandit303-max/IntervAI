from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.interview_orchestrator import InterviewOrchestrator
import app.api.interview as interview_api


TEST_DB = Path(__file__).resolve().parent / "test_sessions.db"


def setup_module() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()
    interview_api.orchestrator = InterviewOrchestrator(
        sessions=SessionRepository(TEST_DB)
    )


def teardown_module() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_exact_start_and_conversation_contract() -> None:
    client = TestClient(app)
    candidate = CandidateRepository().get("CAND-001")

    response = client.post(
        "/api/interview",
        json={"sessionId": "contract-test", "candidate": candidate.model_dump()},
    )
    assert response.status_code == 200
    assert response.json()["done"] is False
    assert "reply" in response.json()

    for index in range(8):
        response = client.post(
            "/api/interview",
            json={"sessionId": "contract-test", "message": f"Mock answer {index + 1}"},
        )

    payload = response.json()
    assert payload["done"] is True
    assert set(payload["feedback"].keys()) == {"summary", "strengths", "gaps", "next"}


def test_unknown_session_returns_404() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/interview",
        json={"sessionId": "missing", "message": "hello"},
    )
    assert response.status_code == 404
