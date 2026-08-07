from app.models.candidate import CandidateMission, CandidateProfile
from app.models.candidate_intelligence import (
    CandidateIntelligence,
    DayLearningSignal,
    LearningState,
    StartingDifficulty,
)
from app.repositories.curriculum_repository import CurriculumRepository


COHORT_DAYS = 31


class CandidateAnalyzer:
    """Turns a sparse candidate profile into deterministic interview priors.

    These are only *priors*. Later interview answers should outweigh profile history.
    Missing mission records are explicitly UNKNOWN, never treated as failure.
    """

    def __init__(self, curriculum: CurriculumRepository | None = None) -> None:
        self.curriculum = curriculum or CurriculumRepository()

    def analyze(self, candidate: CandidateProfile) -> CandidateIntelligence:
        mission_by_day = {mission.day: mission for mission in candidate.missions}
        day_signals: list[DayLearningSignal] = []

        for curriculum_day in self.curriculum.all_days():
            mission = mission_by_day.get(curriculum_day.day)
            day_signals.append(
                self._signal_for_day(
                    day=curriculum_day.day,
                    title=curriculum_day.title,
                    mission=mission,
                )
            )

        completion_rate = self._ratio(candidate.signals.missionsCompleted, COHORT_DAYS)
        first_try_rate = self._ratio(
            candidate.signals.missionsFirstTry,
            max(candidate.signals.missionsCompleted, 1),
        )
        commit_consistency = self._ratio(candidate.signals.commitDays, COHORT_DAYS)
        profile_confidence = self._profile_confidence(
            completion_rate=completion_rate,
            first_try_rate=first_try_rate,
            commit_consistency=commit_consistency,
            observed_days=len(mission_by_day),
        )

        priority_days = [
            signal.day
            for signal in sorted(
                day_signals,
                key=lambda item: (-item.interview_priority, item.day),
            )
            if signal.state is not LearningState.UNKNOWN
        ]

        return CandidateIntelligence(
            candidate_id=candidate.member.id,
            candidate_name=candidate.member.name,
            starting_difficulty=self._starting_difficulty(candidate, first_try_rate),
            profile_confidence=profile_confidence,
            completion_rate=completion_rate,
            first_try_rate=first_try_rate,
            commit_consistency=commit_consistency,
            day_signals=day_signals,
            strong_days=self._days_with_state(day_signals, LearningState.STRONG),
            diagnostic_days=self._days_with_states(
                day_signals,
                {LearningState.DIAGNOSTIC, LearningState.DEVELOPING},
            ),
            failed_days=self._days_with_state(day_signals, LearningState.FAILED),
            skipped_days=self._days_with_state(day_signals, LearningState.SKIPPED),
            unknown_days=self._days_with_state(day_signals, LearningState.UNKNOWN),
            priority_days=priority_days,
        )

    def _signal_for_day(
        self,
        *,
        day: int,
        title: str,
        mission: CandidateMission | None,
    ) -> DayLearningSignal:
        if mission is None:
            return DayLearningSignal(
                day=day,
                title=title,
                state=LearningState.UNKNOWN,
                interview_priority=0.10,
                prior_mastery=None,
                evidence="No mission record is present; treat knowledge as unknown, not failed.",
            )

        if mission.skipped:
            return DayLearningSignal(
                day=day,
                title=title,
                state=LearningState.SKIPPED,
                attempts=mission.attempts,
                interview_priority=0.18,
                prior_mastery=None,
                evidence="Mission was skipped; keep as a gap/revision signal rather than assuming mastery.",
            )

        if mission.passed is False:
            return DayLearningSignal(
                day=day,
                title=title,
                state=LearningState.FAILED,
                attempts=mission.attempts,
                interview_priority=1.00,
                prior_mastery=0.20,
                evidence=f"Mission was not passed after {mission.attempts or 0} recorded attempt(s).",
            )

        # A mission marked neither skipped nor explicitly failed is only considered
        # passed when the supplied profile says passed=true.
        if mission.passed is not True:
            return DayLearningSignal(
                day=day,
                title=title,
                state=LearningState.UNKNOWN,
                attempts=mission.attempts,
                interview_priority=0.10,
                prior_mastery=None,
                evidence="Mission outcome is unspecified; treat knowledge as unknown.",
            )

        attempts = max(mission.attempts or 1, 1)
        if attempts == 1:
            state = LearningState.STRONG
            priority = 0.25
            mastery = 0.80
            evidence = "Mission passed on the first recorded attempt; begin with a stronger prior."
        elif attempts <= 3:
            state = LearningState.DEVELOPING
            priority = 0.60 if attempts == 3 else 0.50
            mastery = 0.65 if attempts == 2 else 0.55
            evidence = (
                f"Mission passed after {attempts} attempts; understanding should be verified in interview."
            )
        else:
            state = LearningState.DIAGNOSTIC
            priority = 0.90 if attempts >= 5 else 0.82
            mastery = 0.40
            evidence = (
                f"Mission passed after {attempts} attempts; use as a high-priority diagnostic topic."
            )

        return DayLearningSignal(
            day=day,
            title=title,
            state=state,
            attempts=attempts,
            interview_priority=priority,
            prior_mastery=mastery,
            evidence=evidence,
        )

    def _starting_difficulty(
        self,
        candidate: CandidateProfile,
        first_try_rate: float,
    ) -> StartingDifficulty:
        role = candidate.member.jobRole.lower()
        years = candidate.member.yearsExperience
        senior_role = any(
            marker in role
            for marker in (
                "senior",
                "principal",
                "distinguished",
                "architect",
            )
        )
        technical_role = any(
            marker in role
            for marker in (
                "engineer",
                "developer",
                "architect",
                "data",
                "devops",
                "computer science",
            )
        )

        # Professional seniority affects how deeply we *start*, while cohort
        # performance prevents experience alone from making the interview unfair.
        if (
            (senior_role and first_try_rate >= 0.45)
            or (technical_role and years >= 8 and first_try_rate >= 0.45)
            or (technical_role and years >= 5 and first_try_rate >= 0.75)
        ):
            return StartingDifficulty.ADVANCED

        if technical_role or years >= 3 or first_try_rate >= 0.35:
            return StartingDifficulty.INTERMEDIATE

        return StartingDifficulty.FOUNDATION

    def _profile_confidence(
        self,
        *,
        completion_rate: float,
        first_try_rate: float,
        commit_consistency: float,
        observed_days: int,
    ) -> float:
        observed_ratio = min(observed_days / COHORT_DAYS, 1.0)
        # Completion and commit behavior are cohort-wide signals; observed mission
        # records are intentionally sparse in the supplied candidate file.
        value = (
            0.40 * completion_rate
            + 0.30 * commit_consistency
            + 0.15 * first_try_rate
            + 0.15 * observed_ratio
        )
        return round(min(max(value, 0.0), 1.0), 3)

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(min(max(numerator / denominator, 0.0), 1.0), 3)

    @staticmethod
    def _days_with_state(
        signals: list[DayLearningSignal],
        state: LearningState,
    ) -> list[int]:
        return [signal.day for signal in signals if signal.state is state]

    @staticmethod
    def _days_with_states(
        signals: list[DayLearningSignal],
        states: set[LearningState],
    ) -> list[int]:
        return [signal.day for signal in signals if signal.state in states]
