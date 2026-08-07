from __future__ import annotations

from collections import defaultdict

from app.config.topic_taxonomy import topics_for_day
from app.models.api import FeedbackPayload
from app.models.answer_evaluation import AnswerEvaluation
from app.models.readiness_report import (
    InterviewReadinessReport,
    ReadinessLevel,
    StruggledQuestion,
)
from app.models.session import InterviewSession, PlannedQuestion
from app.repositories.curriculum_repository import CurriculumRepository
from app.services.candidate_analyzer import CandidateAnalyzer
from app.strategies.coverage_policy import CoveragePolicy


MAX_LIST_ITEMS = 5


class FeedbackService:
    """Aggregates persisted interview evidence into the final readiness report.

    This service is deterministic. It does not add another LLM request at the
    end of the interview, which keeps completion reliable even when the model
    provider is unavailable. Only confidence>0 evaluations are treated as live
    interview evidence; Commit 7 fallback placeholders remain excluded.
    """

    def __init__(
        self,
        *,
        curriculum: CurriculumRepository | None = None,
        coverage: CoveragePolicy | None = None,
        analyzer: CandidateAnalyzer | None = None,
    ) -> None:
        self.curriculum = curriculum or CurriculumRepository()
        self.coverage = coverage or CoveragePolicy()
        self.analyzer = analyzer or CandidateAnalyzer(curriculum=self.curriculum)

    def build_report(self, session: InterviewSession) -> InterviewReadinessReport:
        status = self.coverage.status(session)
        questions_by_id = {question.question_id: question for question in session.questions}
        reliable = [
            (turn, turn.evaluation, questions_by_id.get(turn.question_id))
            for turn in session.turns
            if turn.evaluation is not None
            and turn.evaluation.confidence > 0
            and questions_by_id.get(turn.question_id) is not None
        ]

        dimensions = self._dimension_scores(reliable)
        knowledge_score, knowledge_confidence = self._knowledge_score(session)
        rubric_score = self._rubric_composite(dimensions)

        if reliable:
            overall = round(0.75 * rubric_score + 0.25 * knowledge_score, 1)
            evaluation_confidence = sum(e.confidence for _, e, _ in reliable) / len(reliable)
            evidence_coverage = min(len(reliable) / max(len(session.turns), 1), 1.0)
            report_confidence = round(
                min(1.0, 0.70 * evaluation_confidence * evidence_coverage + 0.30 * knowledge_confidence),
                3,
            )
        else:
            # With no reliable live evaluation, retain a transparent provisional
            # score from the low-confidence candidate-history priors rather than
            # pretending fallback placeholders are interview evidence.
            overall = round(knowledge_score, 1)
            report_confidence = round(min(0.35, knowledge_confidence), 3)

        strongest_topics, weakest_topics = self._rank_topics(session)
        struggled_questions = self._struggled_questions(reliable)
        revisit_days = self._days_to_revisit(session, reliable)
        topics_to_revise = self._topics_to_revise(session, weakest_topics, revisit_days)
        strengths = self._strengths(session, strongest_topics, reliable)
        gaps = self._gaps(session, weakest_topics, reliable)
        next_steps = self._next_steps(topics_to_revise, revisit_days, reliable)

        covered_days = sorted(
            {
                question.day
                for question in session.questions
                if question.question_id in {turn.question_id for turn in session.turns}
            }
        )

        return InterviewReadinessReport(
            overall_score=overall,
            readiness_level=self._readiness_level(overall, report_confidence),
            report_confidence=report_confidence,
            answered_questions=status.answered_questions,
            curriculum_days_covered=covered_days,
            adaptive_followups_used=session.adaptive_followups_used,
            pressure_challenges_used=session.pressure_followups_used,
            technical_accuracy=dimensions["technical_accuracy"],
            conceptual_understanding=dimensions["conceptual_understanding"],
            engineering_reasoning=dimensions["engineering_reasoning"],
            communication_quality=dimensions["communication_quality"],
            answer_depth=dimensions["answer_depth"],
            strongest_topics=strongest_topics,
            weakest_topics=weakest_topics,
            topics_to_revise=topics_to_revise,
            curriculum_days_to_revisit=revisit_days,
            struggled_questions=struggled_questions,
            strengths=strengths,
            gaps=gaps,
            suggested_next_steps=next_steps,
        )

    def to_api_feedback(self, report: InterviewReadinessReport) -> FeedbackPayload:
        confidence_note = (
            "provisional, limited live evaluation evidence"
            if report.report_confidence < 0.35
            else f"confidence {report.report_confidence:.0%}"
        )
        summary = (
            f"Interview completed after {report.answered_questions} answered questions "
            f"covering {len(report.curriculum_days_covered)} curriculum days. "
            f"Readiness: {report.readiness_level.value} ({report.overall_score:.0f}/100; {confidence_note}). "
            f"Conceptual understanding {report.conceptual_understanding:.0f}/100, "
            f"engineering reasoning {report.engineering_reasoning:.0f}/100, "
            f"communication {report.communication_quality:.0f}/100, "
            f"answer depth {report.answer_depth:.0f}/100. "
            f"{report.adaptive_followups_used} adaptive follow-up(s) were used, "
            f"including {report.pressure_challenges_used} pressure challenge(s)."
        )
        return FeedbackPayload(
            summary=summary,
            strengths=report.strengths[:MAX_LIST_ITEMS],
            gaps=report.gaps[:MAX_LIST_ITEMS],
            next=report.suggested_next_steps[:MAX_LIST_ITEMS],
        )

    @staticmethod
    def _weighted_dimension(
        reliable: list[tuple],
        attribute: str,
    ) -> float:
        if not reliable:
            return 50.0
        weighted_sum = 0.0
        total_weight = 0.0
        for _, evaluation, _ in reliable:
            weight = max(evaluation.confidence, 0.01)
            weighted_sum += getattr(evaluation, attribute) * weight
            total_weight += weight
        if total_weight <= 0:
            return 50.0
        return round((weighted_sum / total_weight) / 4.0 * 100.0, 1)

    def _dimension_scores(self, reliable: list[tuple]) -> dict[str, float]:
        return {
            "technical_accuracy": self._weighted_dimension(reliable, "technical_accuracy"),
            "conceptual_understanding": self._weighted_dimension(reliable, "conceptual_understanding"),
            "engineering_reasoning": self._weighted_dimension(reliable, "engineering_reasoning"),
            "communication_quality": self._weighted_dimension(reliable, "communication_clarity"),
            "answer_depth": self._weighted_dimension(reliable, "implementation_depth"),
        }

    @staticmethod
    def _rubric_composite(dimensions: dict[str, float]) -> float:
        return round(
            0.25 * dimensions["technical_accuracy"]
            + 0.25 * dimensions["conceptual_understanding"]
            + 0.20 * dimensions["engineering_reasoning"]
            + 0.15 * dimensions["answer_depth"]
            + 0.15 * dimensions["communication_quality"],
            1,
        )

    @staticmethod
    def _knowledge_score(session: InterviewSession) -> tuple[float, float]:
        if session.knowledge_map is None:
            return 50.0, 0.0
        measured = [
            mastery for mastery in session.knowledge_map.topics.values() if mastery.confidence > 0
        ]
        if not measured:
            return 50.0, 0.0
        total_confidence = sum(item.confidence for item in measured)
        if total_confidence <= 0:
            return 50.0, 0.0
        score = sum(item.score * item.confidence for item in measured) / total_confidence
        confidence = min(1.0, total_confidence / max(len(measured), 1))
        return round(score, 1), round(confidence, 3)

    @staticmethod
    def _rank_topics(session: InterviewSession) -> tuple[list[str], list[str]]:
        if session.knowledge_map is None:
            return [], []
        measured = [
            mastery for mastery in session.knowledge_map.topics.values() if mastery.confidence > 0
        ]
        if not measured:
            return [], []
        strongest = sorted(measured, key=lambda item: (-item.score, -item.confidence, item.topic.value))[:3]
        weakest = sorted(measured, key=lambda item: (item.score, -item.confidence, item.topic.value))[:3]
        return (
            [item.topic.value for item in strongest],
            [item.topic.value for item in weakest],
        )

    @staticmethod
    def _question_score(evaluation: AnswerEvaluation) -> float:
        return round(evaluation.average_score / 4.0 * 100.0, 1)

    def _struggled_questions(self, reliable: list[tuple]) -> list[StruggledQuestion]:
        candidates: list[StruggledQuestion] = []
        for turn, evaluation, question in reliable:
            score = self._question_score(evaluation)
            if score > 65.0 and not evaluation.missing_concepts and not evaluation.misconceptions:
                continue
            reason = self._evaluation_gap_reason(evaluation, score)
            candidates.append(
                StruggledQuestion(
                    question_id=turn.question_id,
                    day=question.day,
                    question=self._truncate(turn.question, 220),
                    score=score,
                    reason=reason,
                )
            )
        candidates.sort(key=lambda item: (item.score, item.day, item.question_id))
        return candidates[:MAX_LIST_ITEMS]

    def _days_to_revisit(self, session: InterviewSession, reliable: list[tuple]) -> list[int]:
        day_scores: dict[int, list[float]] = defaultdict(list)
        day_has_gap: set[int] = set()
        for _, evaluation, question in reliable:
            day_scores[question.day].append(self._question_score(evaluation))
            if evaluation.missing_concepts or evaluation.misconceptions:
                day_has_gap.add(question.day)

        ranked_days: list[tuple[float, int]] = []
        for day, scores in day_scores.items():
            average = sum(scores) / len(scores)
            if average < 70.0 or day in day_has_gap:
                ranked_days.append((average, day))
        ranked_days.sort(key=lambda item: (item[0], item[1]))

        result = [day for _, day in ranked_days]
        intelligence = self.analyzer.analyze(session.candidate)
        # Failed/skipped profile days are revision signals, not proof of interview
        # weakness. Add them only after observed interview gaps.
        for day in [*intelligence.failed_days, *intelligence.skipped_days]:
            if day not in result:
                result.append(day)
            if len(result) >= MAX_LIST_ITEMS:
                break
        return result[:MAX_LIST_ITEMS]

    def _topics_to_revise(
        self,
        session: InterviewSession,
        weakest_topics: list[str],
        revisit_days: list[int],
    ) -> list[str]:
        result: list[str] = []
        if session.knowledge_map is not None:
            for topic in weakest_topics:
                mastery = session.knowledge_map.topics.get(topic)
                if mastery is None:
                    continue
                if mastery.score < 75 or mastery.weak_evidence or mastery.misconceptions:
                    self._append_unique(result, topic)

        for day in revisit_days:
            for topic in topics_for_day(day):
                self._append_unique(result, topic.value)
                if len(result) >= MAX_LIST_ITEMS:
                    return result
        return result[:MAX_LIST_ITEMS]

    def _strengths(
        self,
        session: InterviewSession,
        strongest_topics: list[str],
        reliable: list[tuple],
    ) -> list[str]:
        result: list[str] = []
        if session.knowledge_map is not None:
            for topic in strongest_topics:
                mastery = session.knowledge_map.topics[topic]
                if mastery.score < 65:
                    continue
                self._append_unique(
                    result,
                    f"{topic}: {mastery.score:.0f}/100 mastery from current evidence.",
                )

        strong_points: list[str] = []
        for _, evaluation, question in reliable:
            if evaluation.average_score < 3.0:
                continue
            for point in evaluation.strong_points:
                self._append_unique(strong_points, f"Day {question.day}: {point}")
        for point in strong_points:
            self._append_unique(result, point)
            if len(result) >= MAX_LIST_ITEMS:
                break

        if not result:
            result.append(
                "Completed the required multi-day technical interview; more reliable answer evidence is needed to claim a specific strength."
            )
        return result[:MAX_LIST_ITEMS]

    def _gaps(
        self,
        session: InterviewSession,
        weakest_topics: list[str],
        reliable: list[tuple],
    ) -> list[str]:
        result: list[str] = []
        if session.knowledge_map is not None:
            for topic in weakest_topics:
                mastery = session.knowledge_map.topics[topic]
                if mastery.score < 75:
                    self._append_unique(
                        result,
                        f"{topic}: {mastery.score:.0f}/100 mastery; strengthen this area before interviews.",
                    )

        for _, evaluation, question in reliable:
            for misconception in evaluation.misconceptions:
                self._append_unique(result, f"Day {question.day}: correct misconception — {misconception}")
            for gap in evaluation.missing_concepts:
                self._append_unique(result, f"Day {question.day}: revisit — {gap}")
            if len(result) >= MAX_LIST_ITEMS:
                break

        if not result:
            result.append(
                "No reliable technical gap could be isolated from the available evaluated answers."
            )
        return result[:MAX_LIST_ITEMS]

    def _next_steps(
        self,
        topics_to_revise: list[str],
        revisit_days: list[int],
        reliable: list[tuple],
    ) -> list[str]:
        result: list[str] = []
        for day in revisit_days[:3]:
            curriculum_day = self.curriculum.get_day(day)
            if curriculum_day is not None:
                self._append_unique(result, f"Revisit Day {day} — {curriculum_day.title}.")

        if topics_to_revise:
            self._append_unique(
                result,
                "Practice one implementation/debugging explanation for: "
                + ", ".join(topics_to_revise[:3])
                + ".",
            )

        if reliable:
            self._append_unique(
                result,
                "Re-answer the struggled questions aloud using: decision, trade-off, implementation detail, and failure mode.",
            )
        else:
            self._append_unique(
                result,
                "Run another interview with a configured LLM evaluator so the readiness score is based on live answer evidence.",
            )

        self._append_unique(
            result,
            "Do one timed mock interview focused on concise technical communication and defending engineering choices.",
        )
        return result[:MAX_LIST_ITEMS]

    @staticmethod
    def _evaluation_gap_reason(evaluation: AnswerEvaluation, score: float) -> str:
        pieces: list[str] = []
        if evaluation.missing_concepts:
            pieces.append("missing: " + ", ".join(evaluation.missing_concepts[:2]))
        if evaluation.misconceptions:
            pieces.append("misconception: " + ", ".join(evaluation.misconceptions[:2]))
        if not pieces:
            pieces.append(f"overall answer quality was {score:.0f}/100")
        return "; ".join(pieces)

    @staticmethod
    def _readiness_level(score: float, confidence: float) -> ReadinessLevel:
        # Very low-confidence reports stay provisional rather than claiming the
        # candidate is fully interview-ready from candidate-history priors alone.
        if confidence < 0.20:
            return ReadinessLevel.DEVELOPING
        if score >= 85:
            return ReadinessLevel.STRONG
        if score >= 70:
            return ReadinessLevel.INTERVIEW_READY
        if score >= 50:
            return ReadinessLevel.DEVELOPING
        return ReadinessLevel.NEEDS_FOUNDATION

    @staticmethod
    def _append_unique(target: list[str], value: str) -> None:
        if value and value not in target:
            target.append(value)

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(limit - 1, 0)].rstrip() + "…"
