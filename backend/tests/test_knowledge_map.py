from pathlib import Path
from typing import Any

from app.config.topic_taxonomy import topics_for_day
from app.models.answer_evaluation import AnswerEvaluation, EvaluationSource, RecommendedAction
from app.models.candidate_intelligence import StartingDifficulty
from app.models.interview_plan import QuestionType
from app.models.knowledge_map import KnowledgeTopic
from app.models.session import PlannedQuestion
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.session_repository import SessionRepository
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_orchestrator import InterviewOrchestrator
from app.services.knowledge_map import KnowledgeMapService


TEST_DB = Path(__file__).resolve().parent / "test_knowledge_map_sessions.db"


def strong_evaluation(*, confidence: float = 0.95) -> AnswerEvaluation:
    return AnswerEvaluation(
        technical_accuracy=4,
        conceptual_understanding=4,
        engineering_reasoning=4,
        implementation_depth=4,
        communication_clarity=0,
        strong_points=["Defended the architecture with concrete engineering reasoning."],
        missing_concepts=[],
        misconceptions=[],
        recommended_action=RecommendedAction.SWITCH,
        confidence=confidence,
        evaluator_rationale="The technical answer demonstrates strong mastery even though communication is terse.",
        source=EvaluationSource.LLM,
    )


def day8_question() -> PlannedQuestion:
    return PlannedQuestion(
        question_id="q-vector",
        day=8,
        title="Vector Databases Overview",
        text="When would you use a dedicated vector database?",
        question_type=QuestionType.TRADEOFF,
        difficulty=StartingDifficulty.ADVANCED,
        source_objective="Compare local and managed vector database solutions",
    )


def test_taxonomy_allows_curriculum_days_to_update_overlapping_topics() -> None:
    day8_topics = set(topics_for_day(8))
    assert KnowledgeTopic.RAG in day8_topics
    assert KnowledgeTopic.VECTOR_DATABASES in day8_topics

    day24_topics = set(topics_for_day(24))
    assert KnowledgeTopic.AGENTIC_AI in day24_topics
    assert KnowledgeTopic.MCP in day24_topics
    assert KnowledgeTopic.PRODUCTION_AI_SYSTEMS in day24_topics


def test_initial_map_uses_candidate_history_only_as_low_confidence_prior() -> None:
    candidate = CandidateRepository().get("CAND-003")
    assert candidate is not None

    knowledge_map = KnowledgeMapService().initialize(candidate)
    vector = knowledge_map.topics[KnowledgeTopic.VECTOR_DATABASES.value]
    rag = knowledge_map.topics[KnowledgeTopic.RAG.value]

    assert vector.prior_score == 80.0
    assert rag.prior_score == 80.0
    assert 0.0 < vector.prior_confidence <= 0.35
    assert vector.confidence == vector.prior_confidence
    assert vector.questions_asked == 0
    assert vector.profile_evidence


def test_skipped_or_unknown_days_do_not_create_fake_low_mastery() -> None:
    candidate = CandidateRepository().get("CAND-011")
    assert candidate is not None

    knowledge_map = KnowledgeMapService().initialize(candidate)
    vector = knowledge_map.topics[KnowledgeTopic.VECTOR_DATABASES.value]

    # This candidate skipped the supplied vector-search missions. Skipped/unknown
    # is absence of mastery evidence, not evidence of a score of zero.
    assert vector.prior_score is None
    assert vector.score == 50.0
    assert vector.confidence == 0.0
    assert vector.profile_evidence == []


def test_strong_answer_updates_all_related_topics_with_weighted_evidence() -> None:
    candidate = CandidateRepository().get("CAND-003")
    assert candidate is not None
    service = KnowledgeMapService()
    knowledge_map = service.initialize(candidate)

    before_vector = knowledge_map.topics[KnowledgeTopic.VECTOR_DATABASES.value].score
    before_rag = knowledge_map.topics[KnowledgeTopic.RAG.value].score

    service.update(
        knowledge_map,
        question=day8_question(),
        evaluation=strong_evaluation(),
    )

    vector = knowledge_map.topics[KnowledgeTopic.VECTOR_DATABASES.value]
    rag = knowledge_map.topics[KnowledgeTopic.RAG.value]
    prompt = knowledge_map.topics[KnowledgeTopic.PROMPT_ENGINEERING.value]

    assert vector.score > before_vector
    assert rag.score > before_rag
    assert vector.questions_asked == 1
    assert rag.questions_asked == 1
    assert vector.confidence > vector.prior_confidence
    assert vector.interview_evidence_weight > 0
    assert vector.strong_evidence
    assert vector.last_updated_question_id == "q-vector"
    assert prompt.questions_asked == 0


def test_zero_confidence_fallback_does_not_pollute_knowledge_map() -> None:
    candidate = CandidateRepository().get("CAND-003")
    assert candidate is not None
    service = KnowledgeMapService()
    knowledge_map = service.initialize(candidate)
    before = knowledge_map.model_dump()

    fallback = AnswerEvaluation(
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
        evaluator_rationale="Provider failed, so this is a neutral placeholder rather than candidate evidence.",
        source=EvaluationSource.FALLBACK,
    )

    service.update(knowledge_map, question=day8_question(), evaluation=fallback)
    assert knowledge_map.model_dump() == before


class StrongEvaluationLLM:
    @property
    def enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "technical_accuracy": 4,
            "conceptual_understanding": 4,
            "engineering_reasoning": 4,
            "implementation_depth": 4,
            "communication_clarity": 4,
            "strong_points": ["Connected the answer to a concrete implementation decision."],
            "missing_concepts": [],
            "misconceptions": [],
            "recommended_action": "SWITCH",
            "confidence": 0.94,
            "evaluator_rationale": "The answer provides strong curriculum-grounded technical evidence.",
        }


def test_orchestrator_initializes_updates_and_persists_knowledge_map() -> None:
    if TEST_DB.exists():
        TEST_DB.unlink()

    sessions = SessionRepository(TEST_DB)
    orchestrator = InterviewOrchestrator(
        sessions=sessions,
        answer_evaluator=AnswerEvaluator(llm=StrongEvaluationLLM()),
    )
    candidate = CandidateRepository().get("CAND-003")
    assert candidate is not None

    orchestrator.start("knowledge-map-session", candidate)
    started = sessions.get("knowledge-map-session")
    assert started is not None
    assert started.knowledge_map is not None

    current = started.questions[0]
    affected_topics = topics_for_day(current.day)
    assert affected_topics
    before_counts = {
        topic.value: started.knowledge_map.topics[topic.value].questions_asked
        for topic in affected_topics
    }

    orchestrator.continue_interview(
        "knowledge-map-session",
        "I would connect the curriculum objective to the architecture and validate the trade-offs with measurable tests.",
    )

    stored = sessions.get("knowledge-map-session")
    assert stored is not None
    assert stored.knowledge_map is not None
    for topic in affected_topics:
        mastery = stored.knowledge_map.topics[topic.value]
        assert mastery.questions_asked == before_counts[topic.value] + 1
        assert mastery.last_updated_question_id == current.question_id
        assert mastery.interview_evidence_weight > 0

    if TEST_DB.exists():
        TEST_DB.unlink()
