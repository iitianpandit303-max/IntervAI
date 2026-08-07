from pathlib import Path

from pydantic import ValidationError

from app.llm.client import LLMClient, LLMClientError, OpenAICompatibleLLMClient
from app.llm.schemas import GeneratedQuestionPayload
from app.models.answer_evaluation import AnswerEvaluation, RecommendedAction
from app.models.candidate import CandidateProfile
from app.models.candidate_intelligence import StartingDifficulty
from app.models.interview_plan import QuestionType
from app.models.session import PlannedQuestion, QuestionGenerationSource
from app.repositories.curriculum_repository import CurriculumRepository


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "adaptive_interviewer.md"


class AdaptiveQuestionGenerator:
    """Creates one same-day follow-up from stored evaluation evidence.

    The deterministic fallback is intentionally adaptive too, so the interview
    remains behaviorally correct when no external LLM is configured.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        curriculum: CurriculumRepository | None = None,
    ) -> None:
        self.llm = llm or OpenAICompatibleLLMClient()
        self.curriculum = curriculum or CurriculumRepository()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def generate(
        self,
        *,
        candidate: CandidateProfile,
        previous: PlannedQuestion,
        answer: str,
        evaluation: AnswerEvaluation,
        action: RecommendedAction,
        question_id: str,
    ) -> PlannedQuestion:
        day = self.curriculum.get_day(previous.day)
        difficulty = self._adapt_difficulty(previous.difficulty, action)
        deterministic_text = self._fallback_text(
            previous=previous,
            evaluation=evaluation,
            action=action,
        )

        followup = PlannedQuestion(
            question_id=question_id,
            day=previous.day,
            title=previous.title,
            text=deterministic_text,
            question_type=QuestionType.FOLLOW_UP,
            difficulty=difficulty,
            purpose=f"adaptive {action.value.lower()} follow-up based on the previous answer",
            source_objective=previous.source_objective,
            generation_source=QuestionGenerationSource.FALLBACK,
            generation_rationale="Deterministic adaptive follow-up retained.",
            adaptive_action=action,
            adaptive_from_question_id=previous.question_id,
        )

        if not self.llm.enabled or day is None:
            return followup

        user_prompt = (
            f"Candidate role: {candidate.member.jobRole}\n"
            f"Years of experience: {candidate.member.yearsExperience}\n\n"
            f"Curriculum day: {previous.day} — {previous.title}\n"
            f"Tools: {', '.join(day.tools) if day.tools else 'Not specified'}\n"
            f"Objective: {previous.source_objective or 'Not specified'}\n\n"
            f"Adaptive action: {action.value}\n"
            f"Previous question: {previous.text}\n"
            f"Candidate answer: {answer.strip() or '[empty answer]'}\n\n"
            f"Strong points: {evaluation.strong_points}\n"
            f"Missing concepts: {evaluation.missing_concepts}\n"
            f"Misconceptions: {evaluation.misconceptions}\n"
            f"Evaluator rationale: {evaluation.evaluator_rationale}\n\n"
            "Write the adaptive follow-up now."
        )

        try:
            raw = self.llm.complete_json(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
            generated = GeneratedQuestionPayload.model_validate(raw)
        except (LLMClientError, ValidationError, ValueError, TypeError):
            return followup

        return followup.model_copy(
            update={
                "text": generated.question.strip(),
                "generation_source": QuestionGenerationSource.LLM,
                "generation_rationale": generated.rationale.strip(),
            }
        )

    @staticmethod
    def _fallback_text(
        *,
        previous: PlannedQuestion,
        evaluation: AnswerEvaluation,
        action: RecommendedAction,
    ) -> str:
        focus = None
        if evaluation.misconceptions:
            focus = evaluation.misconceptions[0]
        elif evaluation.missing_concepts:
            focus = evaluation.missing_concepts[0]
        elif previous.source_objective:
            focus = previous.source_objective
        else:
            focus = previous.title

        if action is RecommendedAction.RECOVER:
            return (
                f"Let's make this more concrete. For Day {previous.day} — {previous.title}, "
                f"explain {focus} in your own words and describe the role it plays in the system."
            )
        if action is RecommendedAction.PROBE:
            return (
                f"Stay with Day {previous.day} — {previous.title}. Focus specifically on {focus}. "
                "How would you handle that part in a real implementation?"
            )
        return (
            f"Let's go one level deeper on Day {previous.day} — {previous.title}. Given {focus}, "
            "what additional engineering trade-off or failure mode would you account for in production?"
        )

    @staticmethod
    def _adapt_difficulty(
        current: StartingDifficulty,
        action: RecommendedAction,
    ) -> StartingDifficulty:
        order = [
            StartingDifficulty.FOUNDATION,
            StartingDifficulty.INTERMEDIATE,
            StartingDifficulty.ADVANCED,
        ]
        index = order.index(current)
        if action is RecommendedAction.RECOVER:
            return order[max(0, index - 1)]
        if action is RecommendedAction.DEEPEN:
            return order[min(len(order) - 1, index + 1)]
        return current
