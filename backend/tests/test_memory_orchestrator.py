from pathlib import Path
from typing import Any

from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_orchestrator import InterviewOrchestrator
from app.services.question_generator import QuestionGenerator


TEST_DB = Path(__file__).resolve().parent / "test_memory_sessions.db"


class MemoryCaptureQuestionLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.prompts.append(user_prompt)
        return {
            "question": f"Generated memory-aware technical interview question {len(self.prompts)} about a realistic engineering decision?",
            "rationale": "Valid test question used to inspect working-memory prompt context.",
        }


class DisabledLLM:
    @property
    def enabled(self) -> bool:
        return False

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raise AssertionError("disabled LLM should not be called")


def cleanup() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_next_question_receives_compact_memory_from_previous_answer_and_persists_it() -> None:
    cleanup()
    q_llm = MemoryCaptureQuestionLLM()
    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        question_generator=QuestionGenerator(llm=q_llm),
        answer_evaluator=AnswerEvaluator(llm=DisabledLLM()),
    )
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None

    orchestrator.start("memory-context", candidate)
    assert "No interview answers have been recorded yet" in q_llm.prompts[0]

    orchestrator.continue_interview(
        "memory-context",
        "unique-memory-token: I would inspect retrieval quality before changing the model.",
    )

    assert len(q_llm.prompts) == 2
    assert "unique-memory-token" in q_llm.prompts[1]
    assert "Recent turns" in q_llm.prompts[1]

    stored = sessions.get("memory-context")
    assert stored is not None
    assert stored.memory is not None
    assert stored.memory.last_updated_turn_count == 1
    assert stored.memory.recent_turns[-1].answer.startswith("unique-memory-token")
    cleanup()


class MemoryCaptureEvaluationLLM:
    def __init__(self) -> None:
        self.last_prompt = ""

    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.last_prompt = user_prompt
        return {
            "technical_accuracy": 3,
            "conceptual_understanding": 3,
            "engineering_reasoning": 3,
            "implementation_depth": 3,
            "communication_clarity": 3,
            "strong_points": ["Provides a grounded implementation explanation."],
            "missing_concepts": [],
            "misconceptions": [],
            "recommended_action": "SWITCH",
            "confidence": 0.9,
            "evaluator_rationale": "The current answer is technically sound for the selected objective.",
        }


def test_answer_evaluator_can_receive_prior_working_memory_for_cross_turn_references() -> None:
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None
    question = InterviewOrchestrator().planner.build_plan(candidate)[0]
    llm = MemoryCaptureEvaluationLLM()
    evaluator = AnswerEvaluator(llm=llm)

    evaluator.evaluate(
        candidate=candidate,
        question=question,
        answer="As I said earlier, I would keep the same retrieval boundary.",
        working_memory="Recent turns: candidate previously chose hybrid retrieval for structured and unstructured data.",
    )

    assert "previously chose hybrid retrieval" in llm.last_prompt
    assert "Use prior context only to resolve explicit references" in llm.last_prompt
