from app.models.answer_evaluation import AnswerEvaluation, EvaluationSource, RecommendedAction
from app.models.session import InterviewSession, InterviewTurn
from app.repositories.candidate_repository import CandidateRepository
from app.services.feedback_service import FeedbackService
from app.services.interview_planner import InterviewPlanner
from app.services.knowledge_map import KnowledgeMapService


def _evaluation(
    score: int,
    *,
    confidence: float = 0.9,
    missing: list[str] | None = None,
    misconceptions: list[str] | None = None,
    strong: list[str] | None = None,
) -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_accuracy=score,
        conceptual_understanding=score,
        engineering_reasoning=score,
        implementation_depth=score,
        communication_clarity=score,
        strong_points=strong or [],
        missing_concepts=missing or [],
        misconceptions=misconceptions or [],
        recommended_action=RecommendedAction.SWITCH,
        confidence=confidence,
        evaluator_rationale="Synthetic report test evidence.",
        source=EvaluationSource.LLM if confidence > 0 else EvaluationSource.FALLBACK,
    )


def _session_with_evidence(evaluations: list[AnswerEvaluation]) -> InterviewSession:
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None
    questions = InterviewPlanner().build_plan(candidate)
    knowledge_service = KnowledgeMapService()
    knowledge_map = knowledge_service.initialize(candidate)
    turns: list[InterviewTurn] = []

    for question, evaluation in zip(questions, evaluations):
        turns.append(
            InterviewTurn(
                question_id=question.question_id,
                question=question.text,
                answer="Synthetic candidate answer",
                evaluation=evaluation,
            )
        )
        knowledge_map = knowledge_service.update(
            knowledge_map,
            question=question,
            evaluation=evaluation,
        )

    return InterviewSession(
        session_id="report-test",
        candidate=candidate,
        questions=questions,
        turns=turns,
        current_index=len(turns),
        knowledge_map=knowledge_map,
        done=True,
    )


def test_report_aggregates_rubric_dimensions_and_topics() -> None:
    session = _session_with_evidence(
        [_evaluation(4, strong=["Defended the engineering trade-off clearly."]) for _ in range(8)]
    )

    report = FeedbackService().build_report(session)

    assert report.overall_score >= 90
    assert report.technical_accuracy == 100
    assert report.conceptual_understanding == 100
    assert report.engineering_reasoning == 100
    assert report.communication_quality == 100
    assert report.answer_depth == 100
    assert report.strongest_topics
    assert report.strengths
    assert report.report_confidence > 0.5


def test_report_identifies_struggled_questions_and_revisit_days() -> None:
    evaluations = [_evaluation(4) for _ in range(8)]
    evaluations[0] = _evaluation(
        1,
        missing=["metadata filtering"],
        misconceptions=["cosine similarity generates embeddings"],
    )
    session = _session_with_evidence(evaluations)
    first_day = session.questions[0].day

    report = FeedbackService().build_report(session)

    assert report.struggled_questions
    assert report.struggled_questions[0].day == first_day
    assert first_day in report.curriculum_days_to_revisit
    assert any("metadata filtering" in gap for gap in report.gaps)


def test_zero_confidence_fallbacks_do_not_become_struggled_question_evidence() -> None:
    session = _session_with_evidence([_evaluation(2, confidence=0.0) for _ in range(8)])

    report = FeedbackService().build_report(session)

    assert report.struggled_questions == []
    assert report.report_confidence <= 0.35
    assert report.technical_accuracy == 50.0
    assert any("configured LLM evaluator" in step for step in report.suggested_next_steps)


def test_api_feedback_preserves_exact_required_fields() -> None:
    session = _session_with_evidence([_evaluation(3) for _ in range(8)])
    service = FeedbackService()
    report = service.build_report(session)

    payload = service.to_api_feedback(report).model_dump()

    assert set(payload) == {"summary", "strengths", "gaps", "next"}
    assert "8 answered questions" in payload["summary"]
    assert "curriculum days" in payload["summary"]
    assert payload["strengths"]
    assert payload["gaps"]
    assert payload["next"]
