from app.models.answer_evaluation import (
    AnswerEvaluation,
    EvaluationSource,
    RecommendedAction,
)
from app.models.session import InterviewSession, PlannedQuestion
from app.models.interview_plan import QuestionType
from app.models.candidate_intelligence import StartingDifficulty
from app.repositories.candidate_repository import CandidateRepository
from app.strategies.adaptive_policy import AdaptivePolicy


def evaluation(
    *,
    score: int,
    action: RecommendedAction,
    confidence: float = 0.9,
    missing: list[str] | None = None,
) -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_accuracy=score,
        conceptual_understanding=score,
        engineering_reasoning=score,
        implementation_depth=score,
        communication_clarity=score,
        strong_points=[],
        missing_concepts=missing or [],
        misconceptions=[],
        recommended_action=action,
        confidence=confidence,
        evaluator_rationale="Test evaluation rationale.",
        source=EvaluationSource.LLM,
    )


def session_and_question() -> tuple[InterviewSession, PlannedQuestion]:
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None
    question = PlannedQuestion(
        question_id="q1",
        day=10,
        title="The Retrieval & Matching Engine",
        text="How would you design retrieval?",
        question_type=QuestionType.SYSTEM_DESIGN,
        difficulty=StartingDifficulty.INTERMEDIATE,
    )
    return InterviewSession(session_id="adaptive", candidate=candidate, questions=[question]), question


def test_weak_answer_recovers() -> None:
    session, question = session_and_question()
    decision = AdaptivePolicy().decide(
        session=session,
        current=question,
        evaluation=evaluation(score=1, action=RecommendedAction.PROBE),
    )
    assert decision.action is RecommendedAction.RECOVER
    assert decision.should_insert_followup is True


def test_partial_answer_probes_specific_gap() -> None:
    session, question = session_and_question()
    decision = AdaptivePolicy().decide(
        session=session,
        current=question,
        evaluation=evaluation(
            score=2,
            action=RecommendedAction.PROBE,
            missing=["metadata filtering"],
        ),
    )
    assert decision.action is RecommendedAction.PROBE
    assert decision.should_insert_followup is True


def test_pressure_is_reserved_and_normalized_to_deepen() -> None:
    session, question = session_and_question()
    decision = AdaptivePolicy().decide(
        session=session,
        current=question,
        evaluation=evaluation(score=4, action=RecommendedAction.PRESSURE),
    )
    assert decision.action is RecommendedAction.DEEPEN
    assert decision.should_insert_followup is True


def test_low_confidence_does_not_change_plan() -> None:
    session, question = session_and_question()
    decision = AdaptivePolicy().decide(
        session=session,
        current=question,
        evaluation=evaluation(
            score=1,
            action=RecommendedAction.RECOVER,
            confidence=0.0,
        ),
    )
    assert decision.action is RecommendedAction.SWITCH
    assert decision.should_insert_followup is False


def test_followup_budget_prevents_unbounded_interview() -> None:
    session, question = session_and_question()
    session.adaptive_followups_used = 2
    decision = AdaptivePolicy().decide(
        session=session,
        current=question,
        evaluation=evaluation(score=1, action=RecommendedAction.RECOVER),
    )
    assert decision.action is RecommendedAction.SWITCH
    assert decision.should_insert_followup is False
