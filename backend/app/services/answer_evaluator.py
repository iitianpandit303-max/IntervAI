from pathlib import Path

from pydantic import ValidationError

from app.llm.client import LLMClient, LLMClientError, OpenAICompatibleLLMClient
from app.models.answer_evaluation import (
    AnswerEvaluation,
    EvaluationSource,
    RecommendedAction,
)
from app.models.candidate import CandidateProfile
from app.models.session import PlannedQuestion
from app.repositories.curriculum_repository import CurriculumRepository


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "evaluator.md"


class AnswerEvaluator:
    """Scores one answer against the exact curriculum evidence for its question.

    The evaluator records evidence only; AdaptivePolicy consumes the validated
    result separately so evaluation and interview control remain modular.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        curriculum: CurriculumRepository | None = None,
    ) -> None:
        self.llm = llm or OpenAICompatibleLLMClient()
        self.curriculum = curriculum or CurriculumRepository()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def evaluate(
        self,
        *,
        candidate: CandidateProfile,
        question: PlannedQuestion,
        answer: str,
    ) -> AnswerEvaluation:
        cleaned_answer = answer.strip()
        if not cleaned_answer:
            return self._empty_answer_evaluation()

        if not self.llm.enabled:
            return self._neutral_fallback(
                "LLM evaluation is not configured; neutral low-confidence scores stored."
            )

        day = self.curriculum.get_day(question.day)
        if day is None:
            return self._neutral_fallback(
                "Curriculum day was unavailable; neutral low-confidence scores stored."
            )

        mission = next((item for item in candidate.missions if item.day == question.day), None)
        mission_signal = self._mission_signal(mission)

        user_prompt = (
            f"Candidate role: {candidate.member.jobRole}\n"
            f"Years of experience: {candidate.member.yearsExperience}\n"
            f"Prior learning signal: {mission_signal}\n\n"
            f"Curriculum day: {day.day} — {day.title}\n"
            f"Curriculum type: {day.type}\n"
            f"Tools: {', '.join(day.tools) if day.tools else 'Not specified'}\n"
            f"Primary objective being assessed: {question.source_objective or 'Not specified'}\n\n"
            f"Question type: {question.question_type.value}\n"
            f"Question difficulty: {question.difficulty.value}\n"
            f"Question purpose: {question.purpose}\n"
            f"Interviewer question: {question.text}\n\n"
            f"Candidate answer:\n{cleaned_answer}\n\n"
            "Evaluate this answer now."
        )

        try:
            raw = self.llm.complete_json(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
            evaluation = AnswerEvaluation.model_validate(
                {**raw, "source": EvaluationSource.LLM.value}
            )
        except (LLMClientError, ValidationError, ValueError, TypeError):
            return self._neutral_fallback(
                "LLM evaluation failed validation; neutral low-confidence scores stored."
            )

        return evaluation

    @staticmethod
    def _empty_answer_evaluation() -> AnswerEvaluation:
        return AnswerEvaluation(
            technical_accuracy=0,
            conceptual_understanding=0,
            engineering_reasoning=0,
            implementation_depth=0,
            communication_clarity=0,
            strong_points=[],
            missing_concepts=["No substantive answer was provided."],
            misconceptions=[],
            recommended_action=RecommendedAction.RECOVER,
            confidence=1.0,
            evaluator_rationale="The candidate response was empty after trimming whitespace.",
            source=EvaluationSource.RULE,
        )

    @staticmethod
    def _neutral_fallback(reason: str) -> AnswerEvaluation:
        # Neutral values keep the session schema stable while confidence=0 tells
        # later Knowledge Map logic not to treat these placeholders as evidence.
        return AnswerEvaluation(
            technical_accuracy=2,
            conceptual_understanding=2,
            engineering_reasoning=2,
            implementation_depth=2,
            communication_clarity=2,
            strong_points=[],
            missing_concepts=[],
            misconceptions=[],
            recommended_action=RecommendedAction.SWITCH,
            confidence=0.0,
            evaluator_rationale=reason,
            source=EvaluationSource.FALLBACK,
        )

    @staticmethod
    def _mission_signal(mission) -> str:
        if mission is None:
            return "No mission record supplied for this day; prior knowledge is unknown."
        if mission.skipped:
            return "Mission was skipped."
        if mission.passed is False:
            return f"Mission was not passed after {mission.attempts or 0} attempts."
        if mission.passed is True:
            return f"Mission was passed in {mission.attempts or 1} attempt(s)."
        return "Mission status is unknown."
