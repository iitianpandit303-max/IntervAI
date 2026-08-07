from collections import defaultdict

from app.models.candidate import CandidateProfile
from app.models.candidate_intelligence import (
    CandidateIntelligence,
    DayLearningSignal,
    LearningState,
)
from app.models.interview_plan import QuestionType
from app.models.session import PlannedQuestion
from app.repositories.curriculum_repository import CurriculumRepository
from app.services.candidate_analyzer import CandidateAnalyzer
from app.strategies.coverage_policy import CoveragePolicy


PASSED_STATES = {
    LearningState.STRONG,
    LearningState.DEVELOPING,
    LearningState.DIAGNOSTIC,
}

QUESTION_TYPE_SEQUENCE = [
    QuestionType.CONCEPT,
    QuestionType.IMPLEMENTATION,
    QuestionType.DEBUGGING,
    QuestionType.TRADEOFF,
    QuestionType.SYSTEM_DESIGN,
]


class InterviewPlanner:
    """Builds a deterministic curriculum-grounded interview plan.

    Commit 5 still contains no LLM. The planner decides *where* to interview and
    which engineering style to use. Later commits can replace question wording
    and insert adaptive follow-ups without changing the coverage guarantees.
    """

    def __init__(
        self,
        curriculum: CurriculumRepository | None = None,
        analyzer: CandidateAnalyzer | None = None,
        coverage: CoveragePolicy | None = None,
    ) -> None:
        self.curriculum = curriculum or CurriculumRepository()
        self.analyzer = analyzer or CandidateAnalyzer(self.curriculum)
        self.coverage = coverage or CoveragePolicy()

    def build_plan(self, candidate: CandidateProfile) -> list[PlannedQuestion]:
        intelligence = self.analyzer.analyze(candidate)
        anchors = self._select_anchor_signals(intelligence)

        if len(anchors) < self.coverage.minimum_unique_days:
            raise ValueError("insufficient_curriculum_coverage")

        day_schedule = [signal.day for signal in anchors]

        # After breadth is secured, spend remaining slots deepening the highest
        # priority completed topics. This gives us both breadth and depth while
        # still ending at exactly eight questions for the deterministic milestone.
        repeat_candidates = sorted(
            [signal for signal in anchors if signal.state in PASSED_STATES],
            key=lambda item: (-item.interview_priority, item.day),
        ) or anchors

        repeat_index = 0
        while len(day_schedule) < self.coverage.target_questions:
            day_schedule.append(repeat_candidates[repeat_index % len(repeat_candidates)].day)
            repeat_index += 1

        day_schedule = day_schedule[: self.coverage.target_questions]
        questions = self._questions_from_schedule(day_schedule, intelligence)
        self.coverage.validate_plan(questions)
        return questions

    def _select_anchor_signals(
        self,
        intelligence: CandidateIntelligence,
    ) -> list[DayLearningSignal]:
        signal_by_day = {signal.day: signal for signal in intelligence.day_signals}

        passed = sorted(
            [signal for signal in intelligence.day_signals if signal.state in PASSED_STATES],
            key=lambda item: (-item.interview_priority, item.day),
        )

        # Breadth first: take the strongest interview target from different modules.
        selected: list[DayLearningSignal] = []
        selected_days: set[int] = set()
        selected_modules: set[int] = set()

        for signal in passed:
            module_number = self._module_number_for_day(signal.day)
            if module_number in selected_modules:
                continue
            selected.append(signal)
            selected_days.add(signal.day)
            selected_modules.add(module_number)
            if len(selected) >= self.coverage.target_unique_days:
                break

        # If module diversity does not fill the target, use the next most useful
        # completed days regardless of module.
        for signal in passed:
            if len(selected) >= self.coverage.target_unique_days:
                break
            if signal.day not in selected_days:
                selected.append(signal)
                selected_days.add(signal.day)

        # Sparse synthetic profiles may not contain enough completed missions.
        # Only then fall back in this order: failed -> skipped -> unknown.
        if len(selected) < self.coverage.minimum_unique_days:
            fallback_order = [
                LearningState.FAILED,
                LearningState.SKIPPED,
                LearningState.UNKNOWN,
            ]
            for state in fallback_order:
                fallback = sorted(
                    [signal for signal in intelligence.day_signals if signal.state is state],
                    key=lambda item: (-item.interview_priority, item.day),
                )
                for signal in fallback:
                    if signal.day not in selected_days:
                        selected.append(signal)
                        selected_days.add(signal.day)
                    if len(selected) >= self.coverage.minimum_unique_days:
                        break
                if len(selected) >= self.coverage.minimum_unique_days:
                    break

        # Target five unique days when possible, but four is the hard contract.
        return selected[: self.coverage.target_unique_days]

    def _questions_from_schedule(
        self,
        schedule: list[int],
        intelligence: CandidateIntelligence,
    ) -> list[PlannedQuestion]:
        uses_per_day: dict[int, int] = defaultdict(int)
        questions: list[PlannedQuestion] = []

        for index, day_number in enumerate(schedule, start=1):
            day = self.curriculum.get_day(day_number)
            if day is None:
                raise ValueError(f"unknown_curriculum_day:{day_number}")

            use_index = uses_per_day[day_number]
            uses_per_day[day_number] += 1
            objective = day.objectives[use_index % len(day.objectives)]
            question_type = QUESTION_TYPE_SEQUENCE[(index - 1) % len(QUESTION_TYPE_SEQUENCE)]
            signal = next(
                signal for signal in intelligence.day_signals if signal.day == day_number
            )

            questions.append(
                PlannedQuestion(
                    question_id=f"q{index}",
                    day=day.day,
                    title=day.title,
                    text=self._render_question(
                        index=index,
                        question_type=question_type,
                        day_number=day.day,
                        day_title=day.title,
                        objective=objective,
                    ),
                    question_type=question_type,
                    difficulty=intelligence.starting_difficulty,
                    purpose=self._purpose_for(signal, question_type),
                    source_objective=objective,
                )
            )

        return questions

    def _module_number_for_day(self, day_number: int) -> int:
        for module in self.curriculum.get_curriculum().modules:
            start, end = module.days
            if start <= day_number <= end:
                return module.n
        return 0

    @staticmethod
    def _purpose_for(signal: DayLearningSignal, question_type: QuestionType) -> str:
        if signal.state is LearningState.DIAGNOSTIC:
            reason = "verify a completed topic that required repeated attempts"
        elif signal.state is LearningState.DEVELOPING:
            reason = "verify a completed topic with moderate prior confidence"
        elif signal.state is LearningState.STRONG:
            reason = "test depth beyond a strong completion signal"
        elif signal.state is LearningState.FAILED:
            reason = "diagnose a known learning gap"
        elif signal.state is LearningState.SKIPPED:
            reason = "lightly assess a skipped curriculum area because coverage was sparse"
        else:
            reason = "establish a baseline for an unknown curriculum area"
        return f"{reason}; use a {question_type.value} question"

    @staticmethod
    def _render_question(
        *,
        index: int,
        question_type: QuestionType,
        day_number: int,
        day_title: str,
        objective: str,
    ) -> str:
        prefix = f"Question {index}: Day {day_number} — {day_title}."

        if question_type is QuestionType.CONCEPT:
            body = f"Explain the reasoning behind this objective and why it matters in practice: {objective}"
        elif question_type is QuestionType.IMPLEMENTATION:
            body = f"How would you implement this objective in a real project? Walk through the important steps: {objective}"
        elif question_type is QuestionType.DEBUGGING:
            body = f"Assume an implementation of this objective is giving poor results. How would you debug it systematically? {objective}"
        elif question_type is QuestionType.TRADEOFF:
            body = f"What engineering trade-offs would you consider while achieving this objective? {objective}"
        else:
            body = f"Design a small production-ready approach that satisfies this objective and defend your key decisions: {objective}"

        return f"{prefix} {body}"
