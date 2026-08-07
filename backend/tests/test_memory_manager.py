from app.models.answer_evaluation import AnswerEvaluation, EvaluationSource, RecommendedAction
from app.models.interview_memory import InterviewMemory
from app.models.interview_plan import QuestionType
from app.models.session import InterviewTurn, PlannedQuestion
from app.repositories.candidate_repository import CandidateRepository
from app.services.knowledge_map import KnowledgeMapService
from app.services.memory_manager import MAX_RECENT_TURNS, MemoryManager


def evaluation(
    *,
    score: int = 3,
    confidence: float = 0.9,
    strengths: list[str] | None = None,
    gaps: list[str] | None = None,
    misconceptions: list[str] | None = None,
) -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_accuracy=score,
        conceptual_understanding=score,
        engineering_reasoning=score,
        implementation_depth=score,
        communication_clarity=score,
        strong_points=strengths or [],
        missing_concepts=gaps or [],
        misconceptions=misconceptions or [],
        recommended_action=RecommendedAction.SWITCH,
        confidence=confidence,
        evaluator_rationale="Test evaluation with enough detail for the validated schema.",
        source=EvaluationSource.LLM if confidence > 0 else EvaluationSource.FALLBACK,
    )


def question(number: int, day: int = 10) -> PlannedQuestion:
    return PlannedQuestion(
        question_id=f"q{number}",
        day=day,
        title="The Retrieval & Matching Engine",
        text=f"Technical question {number} about retrieval architecture and trade-offs?",
        question_type=QuestionType.IMPLEMENTATION,
        source_objective="Implement semantic retrieval from the vector database",
    )


def test_memory_captures_reliable_evidence_and_recent_turn() -> None:
    candidate = CandidateRepository().get("CAND-001")
    assert candidate is not None
    knowledge = KnowledgeMapService().initialize(candidate)
    manager = MemoryManager()
    memory = manager.initialize()
    q = question(1)
    ev = evaluation(
        strengths=["Explained semantic retrieval clearly."],
        gaps=["metadata filtering"],
        misconceptions=["Cosine similarity creates embeddings."],
    )
    turn = InterviewTurn(question_id=q.question_id, question=q.text, answer="My answer", evaluation=ev)

    memory = manager.update(
        memory,
        question=q,
        turn=turn,
        knowledge_map=knowledge,
        answered_turn_count=1,
    )

    assert memory.last_updated_turn_count == 1
    assert memory.days_discussed == [10]
    assert "Day 10: Explained semantic retrieval clearly." in memory.strengths
    assert "Day 10: metadata filtering" in memory.unresolved_gaps
    assert "Day 10: Cosine similarity creates embeddings." in memory.misconceptions
    assert memory.recent_turns[-1].answer == "My answer"
    assert "1 answer(s) recorded" in memory.rolling_summary


def test_zero_confidence_evaluation_is_not_remembered_as_candidate_evidence() -> None:
    manager = MemoryManager()
    memory = manager.initialize()
    q = question(1)
    ev = evaluation(confidence=0.0, strengths=["fake strength"], gaps=["fake gap"])
    turn = InterviewTurn(question_id=q.question_id, question=q.text, answer="Answer", evaluation=ev)

    memory = manager.update(
        memory,
        question=q,
        turn=turn,
        knowledge_map=None,
        answered_turn_count=1,
    )

    assert memory.strengths == []
    assert memory.unresolved_gaps == []
    assert "no reliable evidence" in memory.recent_turns[-1].evaluation_summary.lower()


def test_recent_turn_window_stays_bounded() -> None:
    manager = MemoryManager()
    memory = InterviewMemory()

    for index in range(1, 8):
        q = question(index, day=7 + index)
        ev = evaluation()
        turn = InterviewTurn(
            question_id=q.question_id,
            question=q.text,
            answer=f"answer-{index}",
            evaluation=ev,
        )
        memory = manager.update(
            memory,
            question=q,
            turn=turn,
            knowledge_map=None,
            answered_turn_count=index,
        )

    assert len(memory.recent_turns) == MAX_RECENT_TURNS
    assert [turn.question_id for turn in memory.recent_turns] == ["q4", "q5", "q6", "q7"]
    assert "answer-1" not in manager.render_context(memory)
    assert "answer-7" in manager.render_context(memory)


def test_strong_later_evidence_can_close_same_day_gap() -> None:
    manager = MemoryManager()
    memory = manager.initialize()
    q1 = question(1, day=10)
    weak = evaluation(score=2, gaps=["metadata filtering"])
    memory = manager.update(
        memory,
        question=q1,
        turn=InterviewTurn(question_id=q1.question_id, question=q1.text, answer="partial", evaluation=weak),
        knowledge_map=None,
        answered_turn_count=1,
    )
    assert any(item.startswith("Day 10:") for item in memory.unresolved_gaps)

    q2 = question(2, day=10)
    strong = evaluation(score=4, strengths=["Correctly integrated metadata filtering."])
    memory = manager.update(
        memory,
        question=q2,
        turn=InterviewTurn(question_id=q2.question_id, question=q2.text, answer="complete", evaluation=strong),
        knowledge_map=None,
        answered_turn_count=2,
    )

    assert not any(item.startswith("Day 10:") for item in memory.unresolved_gaps)
