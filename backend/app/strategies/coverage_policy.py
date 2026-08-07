from dataclasses import dataclass

from app.models.session import InterviewSession, PlannedQuestion


MIN_QUESTIONS = 8
MIN_UNIQUE_DAYS = 4
TARGET_QUESTIONS = 8
TARGET_UNIQUE_DAYS = 5


@dataclass(frozen=True)
class CoverageStatus:
    answered_questions: int
    unique_answered_days: int
    minimum_questions: int = MIN_QUESTIONS
    minimum_unique_days: int = MIN_UNIQUE_DAYS

    @property
    def requirements_met(self) -> bool:
        return (
            self.answered_questions >= self.minimum_questions
            and self.unique_answered_days >= self.minimum_unique_days
        )


class CoveragePolicy:
    """Deterministically enforces the hackathon's minimum interview coverage."""

    minimum_questions = MIN_QUESTIONS
    minimum_unique_days = MIN_UNIQUE_DAYS
    target_questions = TARGET_QUESTIONS
    target_unique_days = TARGET_UNIQUE_DAYS

    def validate_plan(self, questions: list[PlannedQuestion]) -> None:
        if len(questions) < self.minimum_questions:
            raise ValueError("plan_requires_more_questions")

        unique_days = {question.day for question in questions}
        if len(unique_days) < self.minimum_unique_days:
            raise ValueError("plan_requires_more_curriculum_days")

    def status(self, session: InterviewSession) -> CoverageStatus:
        answered_ids = {turn.question_id for turn in session.turns}
        answered_days = {
            question.day
            for question in session.questions
            if question.question_id in answered_ids
        }
        return CoverageStatus(
            answered_questions=len(session.turns),
            unique_answered_days=len(answered_days),
        )

    def can_finish(self, session: InterviewSession) -> bool:
        return self.status(session).requirements_met
