from pathlib import Path
from typing import Any

from app.models.session import QuestionGenerationSource
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.interview_orchestrator import InterviewOrchestrator
from app.services.question_generator import QuestionGenerator


TEST_DB = Path(__file__).resolve().parent / "test_llm_sessions.db"


class SequencedFakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.calls += 1
        return {
            "question": f"Generated technical interview question number {self.calls}: explain the engineering decision you would make in this scenario.",
            "rationale": "Test-only validated generation.",
        }


def test_orchestrator_generates_questions_just_in_time_and_keeps_contract() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()

    fake = SequencedFakeLLM()
    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        question_generator=QuestionGenerator(llm=fake),
    )
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    start = orchestrator.start("llm-contract", candidate)
    assert start.done is False
    assert "Generated technical interview question number 1" in start.reply

    stored = sessions.get("llm-contract")
    assert stored is not None
    assert stored.questions[0].generation_source == QuestionGenerationSource.LLM
    assert stored.questions[1].generation_source == QuestionGenerationSource.DETERMINISTIC

    second = orchestrator.continue_interview("llm-contract", "My first answer")
    assert "Generated technical interview question number 2" in second.reply

    stored = sessions.get("llm-contract")
    assert stored is not None
    assert stored.questions[1].generation_source == QuestionGenerationSource.LLM
    assert fake.calls == 2

    if TEST_DB.exists():
        TEST_DB.unlink()
