from app.models.candidate_intelligence import LearningState, StartingDifficulty
from app.repositories.candidate_repository import CandidateRepository
from app.services.candidate_analyzer import CandidateAnalyzer


def _analysis(candidate_id: str):
    candidates = CandidateRepository()
    candidate = candidates.get(candidate_id)
    assert candidate is not None
    return CandidateAnalyzer().analyze(candidate)


def _day(analysis, day: int):
    return next(signal for signal in analysis.day_signals if signal.day == day)


def test_high_performer_gets_strong_priors_and_advanced_start() -> None:
    analysis = _analysis("CAND-003")

    assert analysis.starting_difficulty == StartingDifficulty.ADVANCED
    assert 7 in analysis.strong_days
    assert 8 in analysis.strong_days
    assert _day(analysis, 23).state == LearningState.STRONG
    assert analysis.first_try_rate > 0.9


def test_failed_and_skipped_missions_are_distinct_signals() -> None:
    analysis = _analysis("CAND-010")

    assert _day(analysis, 8).state == LearningState.FAILED
    assert _day(analysis, 10).state == LearningState.FAILED
    assert _day(analysis, 27).state == LearningState.SKIPPED
    assert _day(analysis, 28).state == LearningState.SKIPPED
    assert _day(analysis, 8).interview_priority > _day(analysis, 27).interview_priority


def test_missing_mission_is_unknown_not_failed() -> None:
    analysis = _analysis("CAND-011")

    # Day 10 does not appear in this candidate's sparse mission list.
    day_10 = _day(analysis, 10)
    assert day_10.state == LearningState.UNKNOWN
    assert day_10.prior_mastery is None
    assert 10 in analysis.unknown_days
    assert 10 not in analysis.failed_days


def test_repeated_attempt_pass_becomes_diagnostic_priority() -> None:
    analysis = _analysis("CAND-017")

    day_8 = _day(analysis, 8)
    assert day_8.state == LearningState.DIAGNOSTIC
    assert day_8.attempts == 5
    assert day_8.interview_priority >= 0.9
    assert 8 in analysis.diagnostic_days


def test_priority_days_favor_failure_and_repeated_attempts_over_skips() -> None:
    analysis = _analysis("CAND-016")

    # Failed Day 12 should rank ahead of skipped Day 27.
    assert analysis.priority_days.index(12) < analysis.priority_days.index(27)
    assert analysis.priority_days.index(7) < analysis.priority_days.index(28)


def test_analysis_covers_every_curriculum_day() -> None:
    analysis = _analysis("CAND-002")

    assert len(analysis.day_signals) == 31
    assert len({signal.day for signal in analysis.day_signals}) == 31
    assert 0.0 <= analysis.profile_confidence <= 1.0


def test_skipped_topics_are_lower_priority_than_completed_strong_topics() -> None:
    analysis = _analysis("CAND-007")

    assert _day(analysis, 7).state == LearningState.DEVELOPING
    assert _day(analysis, 27).state == LearningState.SKIPPED
    assert _day(analysis, 7).interview_priority > _day(analysis, 27).interview_priority
