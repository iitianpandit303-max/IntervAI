from pathlib import Path

from pydantic import ValidationError

from app.llm.client import LLMClient, LLMClientError, OpenAICompatibleLLMClient
from app.llm.schemas import GeneratedQuestionPayload
from app.models.answer_evaluation import AnswerEvaluation, RecommendedAction
from app.models.candidate import CandidateProfile
from app.models.candidate_intelligence import StartingDifficulty
from app.models.interview_plan import QuestionType
from app.models.pressure import PressureChallengeType
from app.models.session import PlannedQuestion, QuestionGenerationSource
from app.repositories.curriculum_repository import CurriculumRepository
from app.strategies.pressure_mode import PressureModeStrategy


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "pressure_interviewer.md"


class PressureQuestionGenerator:
    """Generates one professional assumption/trade-off challenge.

    The challenge type is selected deterministically. The LLM only words the
    challenge using the actual candidate answer. A deterministic fallback keeps
    Pressure Mode functional when the provider is unavailable.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        curriculum: CurriculumRepository | None = None,
        strategy: PressureModeStrategy | None = None,
    ) -> None:
        self.llm = llm or OpenAICompatibleLLMClient()
        self.curriculum = curriculum or CurriculumRepository()
        self.strategy = strategy or PressureModeStrategy()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def generate(
        self,
        *,
        candidate: CandidateProfile,
        previous: PlannedQuestion,
        answer: str,
        evaluation: AnswerEvaluation,
        question_id: str,
    ) -> PlannedQuestion:
        day = self.curriculum.get_day(previous.day)
        challenge_type = self.strategy.select_challenge(previous)
        difficulty = self._raise_difficulty(previous.difficulty)

        pressure = PlannedQuestion(
            question_id=question_id,
            day=previous.day,
            title=previous.title,
            text=self._fallback_text(previous, challenge_type),
            question_type=QuestionType.PRESSURE,
            difficulty=difficulty,
            purpose=(
                "pressure challenge: test whether the candidate can defend or revise "
                "a strong engineering decision"
            ),
            source_objective=previous.source_objective,
            generation_source=QuestionGenerationSource.FALLBACK,
            generation_rationale=(
                f"Deterministic {challenge_type.value} pressure challenge retained."
            ),
            adaptive_action=RecommendedAction.PRESSURE,
            adaptive_from_question_id=previous.question_id,
            pressure_challenge_type=challenge_type,
        )

        if not self.llm.enabled or day is None:
            return pressure

        user_prompt = (
            f"Candidate role: {candidate.member.jobRole}\n"
            f"Years of experience: {candidate.member.yearsExperience}\n\n"
            f"Curriculum day: {previous.day} — {previous.title}\n"
            f"Tools: {', '.join(day.tools) if day.tools else 'Not specified'}\n"
            f"Objective: {previous.source_objective or 'Not specified'}\n\n"
            f"Pressure challenge type: {challenge_type.value}\n"
            f"Previous question: {previous.text}\n"
            f"Candidate answer: {answer.strip()}\n\n"
            f"Strong points: {evaluation.strong_points}\n"
            f"Evaluator rationale: {evaluation.evaluator_rationale}\n\n"
            "Write one professional pressure challenge now."
        )

        try:
            raw = self.llm.complete_json(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
            generated = GeneratedQuestionPayload.model_validate(raw)
        except (LLMClientError, ValidationError, ValueError, TypeError):
            return pressure

        return pressure.model_copy(
            update={
                "text": generated.question.strip(),
                "generation_source": QuestionGenerationSource.LLM,
                "generation_rationale": generated.rationale.strip(),
            }
        )

    @staticmethod
    def _fallback_text(
        previous: PlannedQuestion,
        challenge_type: PressureChallengeType,
    ) -> str:
        topic = f"Day {previous.day} — {previous.title}"
        if challenge_type is PressureChallengeType.ALTERNATIVE:
            return (
                f"Challenge your own decision for {topic}: what credible alternative would you "
                "consider, and under what conditions would that alternative be the better choice?"
            )
        if challenge_type is PressureChallengeType.COUNTERFACTUAL:
            return (
                f"Suppose one important assumption behind your {topic} approach turns out to be "
                "wrong in production. Which assumption would you test first, and how would your implementation change?"
            )
        if challenge_type is PressureChallengeType.CONSTRAINT:
            return (
                f"Now add a production constraint to your {topic} design: traffic and reliability "
                "requirements increase sharply while cost must stay controlled. What breaks first, and what would you change?"
            )
        return (
            f"For {topic}, identify the strongest assumption behind the approach you just defended. "
            "What evidence or operating condition would make you change that decision?"
        )

    @staticmethod
    def _raise_difficulty(current: StartingDifficulty) -> StartingDifficulty:
        if current is StartingDifficulty.FOUNDATION:
            return StartingDifficulty.INTERMEDIATE
        return StartingDifficulty.ADVANCED
