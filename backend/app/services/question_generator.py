from pathlib import Path

from pydantic import ValidationError

from app.llm.client import LLMClient, LLMClientError, OpenAICompatibleLLMClient
from app.llm.schemas import GeneratedQuestionPayload
from app.models.candidate import CandidateProfile
from app.models.session import PlannedQuestion, QuestionGenerationSource
from app.repositories.curriculum_repository import CurriculumRepository


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "interviewer.md"


class QuestionGenerator:
    """Turns a deterministic planned question into natural LLM wording.

    Coverage/day/type/difficulty remain owned by backend policy. If the model is
    unavailable or returns malformed JSON, the deterministic planner question is
    preserved so the evaluator contract can continue safely.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        curriculum: CurriculumRepository | None = None,
    ) -> None:
        self.llm = llm or OpenAICompatibleLLMClient()
        self.curriculum = curriculum or CurriculumRepository()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def materialize(
        self,
        *,
        candidate: CandidateProfile,
        planned: PlannedQuestion,
        working_memory: str | None = None,
    ) -> PlannedQuestion:
        if planned.generation_source is not QuestionGenerationSource.DETERMINISTIC:
            return planned

        if not self.llm.enabled:
            return planned.model_copy(
                update={
                    "generation_source": QuestionGenerationSource.FALLBACK,
                    "generation_rationale": "LLM is not configured; deterministic question retained.",
                }
            )

        day = self.curriculum.get_day(planned.day)
        if day is None:
            return planned.model_copy(
                update={
                    "generation_source": QuestionGenerationSource.FALLBACK,
                    "generation_rationale": "Curriculum day was unavailable; deterministic question retained.",
                }
            )

        mission = next((item for item in candidate.missions if item.day == planned.day), None)
        mission_signal = self._mission_signal(mission)

        user_prompt = (
            f"Candidate name: {candidate.member.name}\n"
            f"Candidate role: {candidate.member.jobRole}\n"
            f"Years of experience: {candidate.member.yearsExperience}\n"
            f"Relevant mission signal: {mission_signal}\n\n"
            f"Curriculum day: {day.day} — {day.title}\n"
            f"Curriculum type: {day.type}\n"
            f"Tools: {', '.join(day.tools) if day.tools else 'Not specified'}\n"
            f"Objective to assess: {planned.source_objective or 'Not specified'}\n\n"
            f"Question type: {planned.question_type.value}\n"
            f"Difficulty: {planned.difficulty.value}\n"
            f"Planner purpose: {planned.purpose}\n\n"
            f"{working_memory or 'No prior interview context is available yet.'}\n\n"
            "Use prior context only when it makes the question more coherent; do not reveal internal scores or memory labels.\n"
            "Write the interview question now."
        )

        try:
            raw = self.llm.complete_json(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
            generated = GeneratedQuestionPayload.model_validate(raw)
        except (LLMClientError, ValidationError, ValueError, TypeError):
            return planned.model_copy(
                update={
                    "generation_source": QuestionGenerationSource.FALLBACK,
                    "generation_rationale": "LLM generation failed validation; deterministic question retained.",
                }
            )

        return planned.model_copy(
            update={
                "text": generated.question.strip(),
                "generation_source": QuestionGenerationSource.LLM,
                "generation_rationale": generated.rationale.strip(),
            }
        )

    @staticmethod
    def _mission_signal(mission) -> str:
        if mission is None:
            return "No mission record supplied for this day. Treat prior knowledge as unknown."
        if mission.skipped:
            return "Mission was skipped."
        if mission.passed is False:
            return f"Mission was not passed after {mission.attempts or 0} attempts."
        if mission.passed is True:
            return f"Mission was passed in {mission.attempts or 1} attempt(s)."
        return "Mission status is unknown."
