from app.models.candidate import CandidateMember, CandidateProfile, CandidateSignals
from app.models.candidate_intelligence import LearningState
from app.models.interview_plan import QuestionType
from app.repositories.candidate_repository import CandidateRepository
from app.services.candidate_analyzer import CandidateAnalyzer
from app.services.interview_planner import InterviewPlanner
from app.strategies.coverage_policy import MIN_QUESTIONS, MIN_UNIQUE_DAYS


def test_plan_guarantees_eight_questions_and_four_days() -> None:
    candidate = CandidateRepository().get("CAND-002")
    questions = InterviewPlanner().build_plan(candidate)

    assert len(questions) == MIN_QUESTIONS
    assert len({question.day for question in questions}) >= MIN_UNIQUE_DAYS


def test_planner_prefers_completed_days_for_normal_profiles() -> None:
    candidate = CandidateRepository().get("CAND-010")
    analyzer = CandidateAnalyzer()
    intelligence = analyzer.analyze(candidate)
    state_by_day = {signal.day: signal.state for signal in intelligence.day_signals}

    questions = InterviewPlanner().build_plan(candidate)

    # Gerald has enough passed missions, so failed/skipped curriculum should remain
    # signals rather than becoming anchor questions in this milestone.
    assert all(state_by_day[question.day] in {
        LearningState.STRONG,
        LearningState.DEVELOPING,
        LearningState.DIAGNOSTIC,
    } for question in questions)


def test_plan_uses_multiple_question_styles() -> None:
    candidate = CandidateRepository().get("CAND-001")
    questions = InterviewPlanner().build_plan(candidate)

    types = {question.question_type for question in questions}
    assert QuestionType.CONCEPT in types
    assert QuestionType.IMPLEMENTATION in types
    assert QuestionType.DEBUGGING in types
    assert QuestionType.TRADEOFF in types
    assert QuestionType.SYSTEM_DESIGN in types


def test_high_attempt_passed_days_receive_depth_slots() -> None:
    candidate = CandidateRepository().get("CAND-002")
    questions = InterviewPlanner().build_plan(candidate)
    counts: dict[int, int] = {}
    for question in questions:
        counts[question.day] = counts.get(question.day, 0) + 1

    # Candidate 002 required five attempts on Day 12; after breadth is secured,
    # the planner should use a remaining slot to deepen a high-priority completed day.
    assert counts.get(12, 0) >= 2


def test_sparse_profile_still_meets_contract_with_fallback() -> None:
    candidate = CandidateProfile(
        member=CandidateMember(
            id="SPARSE-1",
            name="Sparse Candidate",
            jobRole="Student",
            yearsExperience=0,
            education="B.Tech",
            status="COMPLETED",
        ),
        missions=[],
        signals=CandidateSignals(commitDays=0, missionsCompleted=0, missionsFirstTry=0),
    )

    questions = InterviewPlanner().build_plan(candidate)

    assert len(questions) == MIN_QUESTIONS
    assert len({question.day for question in questions}) >= MIN_UNIQUE_DAYS
