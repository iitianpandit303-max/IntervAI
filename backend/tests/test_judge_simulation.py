from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.interview_orchestrator import InterviewOrchestrator
import app.api.interview as interview_api


TEST_DB = Path(__file__).resolve().parent / "test_judge_simulation.db"


def setup_module() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()
    interview_api.orchestrator = InterviewOrchestrator(
        sessions=SessionRepository(TEST_DB)
    )


def teardown_module() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_openapi_keeps_hidden_ui_get_out_of_evaluator_contract() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert set(paths["/api/interview"].keys()) == {"post"}


def test_request_shape_rejects_start_and_message_in_same_call() -> None:
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None
    response = TestClient(app).post(
        "/api/interview",
        json={
            "sessionId": "invalid-shape",
            "candidate": candidate.model_dump(),
            "message": "this must not be accepted together",
        },
    )
    assert response.status_code == 422


def test_all_supplied_candidates_complete_the_exact_judge_flow() -> None:
    """Contract-level smoke simulation across all 20 synthetic profiles.

    LLM credentials are intentionally absent in CI/test mode, exercising the
    deterministic fallback path that must still satisfy the evaluator minimums.
    """

    client = TestClient(app)
    candidates = CandidateRepository().all()
    assert len(candidates) == 20

    for candidate in candidates:
        session_id = f"judge-{candidate.member.id.lower()}"
        started = client.post(
            "/api/interview",
            json={"sessionId": session_id, "candidate": candidate.model_dump()},
        )
        assert started.status_code == 200
        assert set(started.json()) == {"reply", "done"}
        assert started.json()["done"] is False

        final = None
        for turn in range(12):
            response = client.post(
                "/api/interview",
                json={
                    "sessionId": session_id,
                    "message": (
                        "I would explain the concept, justify the engineering trade-off, "
                        f"and validate the implementation with tests. Turn {turn + 1}."
                    ),
                },
            )
            assert response.status_code == 200
            final = response.json()
            if final["done"]:
                break

        assert final is not None and final["done"] is True
        assert set(final) == {"reply", "done", "feedback"}
        assert set(final["feedback"]) == {"summary", "strengths", "gaps", "next"}

        insights = client.get(
            "/api/interview", params={"sessionId": session_id}
        ).json()
        assert insights["answeredQuestions"] >= 8
        assert len(insights["curriculumDaysCovered"]) >= 4
        assert insights["finalReport"] is not None
