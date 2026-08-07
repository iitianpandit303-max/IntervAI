from typing import Any

from app.models.answer_evaluation import AnswerEvaluation, EvaluationSource, RecommendedAction
from app.models.candidate_intelligence import StartingDifficulty
from app.models.interview_plan import QuestionType
from app.models.pressure import PressureChallengeType
from app.models.session import PlannedQuestion, QuestionGenerationSource
from app.repositories.candidate_repository import CandidateRepository
from app.services.pressure_question_generator import PressureQuestionGenerator
from app.strategies.pressure_mode import PressureModeStrategy


class DisabledLLM:
    @property
    def enabled(self) -> bool:
        return False

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raise AssertionError("Disabled LLM should never be called")


class PressureLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        assert "Pressure challenge type: alternative" in user_prompt
        assert "Candidate answer:" in user_prompt
        assert "serious interviewer" in system_prompt
        return {
            "question": (
                "You chose a dedicated vector database, but PostgreSQL can also store vectors. "
                "For a small workload, why is the extra service justified?"
            ),
            "rationale": "Challenges the candidate's database choice with a credible alternative.",
        }


def evaluation() -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_accuracy=4,
        conceptual_understanding=4,
        engineering_reasoning=4,
        implementation_depth=3,
        communication_clarity=4,
        strong_points=["Compared vector-store design options."],
        missing_concepts=[],
        misconceptions=[],
        recommended_action=RecommendedAction.PRESSURE,
        confidence=0.94,
        evaluator_rationale="The answer makes a concrete datastore choice worth defending.",
        source=EvaluationSource.LLM,
    )


def question(question_type: QuestionType) -> PlannedQuestion:
    return PlannedQuestion(
        question_id="q1",
        day=8,
        title="Vector Databases Overview",
        text="When would you choose a managed vector database?",
        question_type=question_type,
        difficulty=StartingDifficulty.INTERMEDIATE,
        source_objective="Compare local and managed vector database solutions",
    )


def test_pressure_strategy_maps_question_styles_to_challenge_types() -> None:
    strategy = PressureModeStrategy()
    assert strategy.select_challenge(question(QuestionType.CONCEPT)) is PressureChallengeType.ASSUMPTION
    assert strategy.select_challenge(question(QuestionType.TRADEOFF)) is PressureChallengeType.ALTERNATIVE
    assert strategy.select_challenge(question(QuestionType.DEBUGGING)) is PressureChallengeType.COUNTERFACTUAL
    assert strategy.select_challenge(question(QuestionType.SYSTEM_DESIGN)) is PressureChallengeType.CONSTRAINT


def test_pressure_generator_uses_llm_and_marks_question_as_pressure() -> None:
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None
    generated = PressureQuestionGenerator(llm=PressureLLM()).generate(
        candidate=candidate,
        previous=question(QuestionType.TRADEOFF),
        answer="I would use Pinecone because I want managed scaling and operations.",
        evaluation=evaluation(),
        question_id="q1-p1",
    )

    assert generated.question_type is QuestionType.PRESSURE
    assert generated.adaptive_action is RecommendedAction.PRESSURE
    assert generated.pressure_challenge_type is PressureChallengeType.ALTERNATIVE
    assert generated.adaptive_from_question_id == "q1"
    assert generated.generation_source is QuestionGenerationSource.LLM
    assert "PostgreSQL" in generated.text
    assert generated.difficulty is StartingDifficulty.ADVANCED


def test_pressure_generator_has_deterministic_fallback() -> None:
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None
    generated = PressureQuestionGenerator(llm=DisabledLLM()).generate(
        candidate=candidate,
        previous=question(QuestionType.SYSTEM_DESIGN),
        answer="I would use a managed service.",
        evaluation=evaluation(),
        question_id="q1-p1",
    )

    assert generated.generation_source is QuestionGenerationSource.FALLBACK
    assert generated.pressure_challenge_type is PressureChallengeType.CONSTRAINT
    assert "production constraint" in generated.text.lower()
