from app.config.topic_taxonomy import TOPIC_DAYS, topics_for_day
from app.models.answer_evaluation import AnswerEvaluation
from app.models.candidate import CandidateProfile
from app.models.candidate_intelligence import StartingDifficulty
from app.models.interview_plan import QuestionType
from app.models.knowledge_map import CandidateKnowledgeMap, KnowledgeTopic, TopicMastery
from app.models.session import PlannedQuestion
from app.services.candidate_analyzer import CandidateAnalyzer


QUESTION_WEIGHTS: dict[QuestionType, float] = {
    QuestionType.CONCEPT: 0.80,
    QuestionType.IMPLEMENTATION: 1.00,
    QuestionType.DEBUGGING: 1.10,
    QuestionType.TRADEOFF: 1.20,
    QuestionType.SYSTEM_DESIGN: 1.30,
    QuestionType.FOLLOW_UP: 1.10,
    QuestionType.PRESSURE: 1.25,
}

DIFFICULTY_WEIGHTS: dict[StartingDifficulty, float] = {
    StartingDifficulty.FOUNDATION: 0.90,
    StartingDifficulty.INTERMEDIATE: 1.00,
    StartingDifficulty.ADVANCED: 1.15,
}


class KnowledgeMapService:
    """Maintains explainable mastery estimates across the interview.

    Candidate history creates only a low-confidence prior. Interview answers are
    stronger evidence and progressively dominate the score. Communication is
    intentionally excluded from topic mastery because the map represents
    technical knowledge; communication remains available for the final report.
    """

    def __init__(self, analyzer: CandidateAnalyzer | None = None) -> None:
        self.analyzer = analyzer or CandidateAnalyzer()

    def initialize(self, candidate: CandidateProfile) -> CandidateKnowledgeMap:
        intelligence = self.analyzer.analyze(candidate)
        signal_by_day = {signal.day: signal for signal in intelligence.day_signals}
        topics: dict[str, TopicMastery] = {}

        for topic, related_days in TOPIC_DAYS.items():
            observed = [
                signal_by_day[day]
                for day in related_days
                if day in signal_by_day and signal_by_day[day].prior_mastery is not None
            ]

            if observed:
                prior_score = round(
                    100 * sum(signal.prior_mastery or 0.0 for signal in observed) / len(observed),
                    1,
                )
                # Candidate history is useful for choosing where to start, but it
                # must stay weaker than evidence from the live interview.
                prior_confidence = round(
                    min(
                        0.35,
                        intelligence.profile_confidence
                        * min(len(observed) / 2.0, 1.0)
                        * 0.35,
                    ),
                    3,
                )
                score = prior_score
            else:
                prior_score = None
                prior_confidence = 0.0
                score = 50.0

            profile_evidence = [signal.evidence for signal in observed[:4]]
            topics[topic.value] = TopicMastery(
                topic=topic,
                score=score,
                confidence=prior_confidence,
                prior_score=prior_score,
                prior_confidence=prior_confidence,
                related_days=list(related_days),
                profile_evidence=profile_evidence,
            )

        return CandidateKnowledgeMap(candidate_id=candidate.member.id, topics=topics)

    def update(
        self,
        knowledge_map: CandidateKnowledgeMap,
        *,
        question: PlannedQuestion,
        evaluation: AnswerEvaluation,
    ) -> CandidateKnowledgeMap:
        # Commit 7 deliberately uses confidence=0 for model failures. Never let
        # fallback placeholders change mastery or confidence.
        if evaluation.confidence <= 0.0:
            return knowledge_map

        relevant_topics = topics_for_day(question.day)
        if not relevant_topics:
            return knowledge_map

        answer_score = self._technical_mastery_score(evaluation)
        evidence_weight = self._evidence_weight(question, evaluation)

        for topic in relevant_topics:
            mastery = knowledge_map.topics[topic.value]
            old_weight = mastery.prior_confidence + mastery.interview_evidence_weight
            total_weight = old_weight + evidence_weight

            if total_weight > 0:
                mastery.score = round(
                    ((mastery.score * old_weight) + (answer_score * evidence_weight))
                    / total_weight,
                    1,
                )
            else:
                mastery.score = answer_score

            mastery.interview_evidence_weight = round(
                mastery.interview_evidence_weight + evidence_weight,
                3,
            )
            mastery.questions_asked += 1
            mastery.confidence = round(
                min(
                    1.0,
                    (mastery.prior_confidence + mastery.interview_evidence_weight) / 2.5,
                ),
                3,
            )
            mastery.last_updated_question_id = question.question_id

            self._append_evidence(
                mastery=mastery,
                question=question,
                evaluation=evaluation,
                answer_score=answer_score,
            )

        return knowledge_map

    @staticmethod
    def _technical_mastery_score(evaluation: AnswerEvaluation) -> float:
        technical_dimensions = [
            evaluation.technical_accuracy,
            evaluation.conceptual_understanding,
            evaluation.engineering_reasoning,
            evaluation.implementation_depth,
        ]
        return round((sum(technical_dimensions) / len(technical_dimensions)) / 4.0 * 100, 1)

    @staticmethod
    def _evidence_weight(
        question: PlannedQuestion,
        evaluation: AnswerEvaluation,
    ) -> float:
        weight = (
            evaluation.confidence
            * QUESTION_WEIGHTS[question.question_type]
            * DIFFICULTY_WEIGHTS[question.difficulty]
        )
        return round(weight, 3)

    @staticmethod
    def _append_evidence(
        *,
        mastery: TopicMastery,
        question: PlannedQuestion,
        evaluation: AnswerEvaluation,
        answer_score: float,
    ) -> None:
        prefix = f"Day {question.day} / {question.question_type.value}: "

        if answer_score >= 75.0:
            points = evaluation.strong_points or [
                f"demonstrated strong technical understanding ({answer_score:.0f}/100)."
            ]
            for point in points:
                KnowledgeMapService._append_unique(
                    mastery.strong_evidence,
                    f"{prefix}{point}",
                    limit=12,
                )

        if answer_score <= 60.0 or evaluation.missing_concepts:
            gaps = evaluation.missing_concepts or [
                f"technical depth remained limited ({answer_score:.0f}/100)."
            ]
            for gap in gaps:
                KnowledgeMapService._append_unique(
                    mastery.weak_evidence,
                    f"{prefix}{gap}",
                    limit=12,
                )

        for misconception in evaluation.misconceptions:
            KnowledgeMapService._append_unique(
                mastery.misconceptions,
                f"{prefix}{misconception}",
                limit=12,
            )

    @staticmethod
    def _append_unique(target: list[str], value: str, *, limit: int) -> None:
        if value in target:
            return
        target.append(value)
        if len(target) > limit:
            del target[:-limit]
