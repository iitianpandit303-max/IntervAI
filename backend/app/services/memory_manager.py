from app.models.interview_memory import InterviewMemory, MemoryTurn
from app.models.knowledge_map import CandidateKnowledgeMap
from app.models.session import InterviewTurn, PlannedQuestion


MAX_RECENT_TURNS = 4
MAX_MEMORY_ITEMS = 8
MAX_TEXT_FIELD_CHARS = 600
MAX_CONTEXT_CHARS = 6500


class MemoryManager:
    """Builds bounded working memory while preserving the full transcript.

    This service never asks the LLM to summarize. It derives a compact,
    deterministic memory from validated evaluations and the Knowledge Map,
    avoiding an extra model call per turn and keeping behavior predictable.
    """

    def initialize(self) -> InterviewMemory:
        return InterviewMemory()

    def update(
        self,
        memory: InterviewMemory,
        *,
        question: PlannedQuestion,
        turn: InterviewTurn,
        knowledge_map: CandidateKnowledgeMap | None,
        answered_turn_count: int,
    ) -> InterviewMemory:
        evaluation = turn.evaluation
        evaluation_summary = self._evaluation_summary(turn)

        recent_turn = MemoryTurn(
            question_id=question.question_id,
            day=question.day,
            question=self._truncate(question.text),
            answer=self._truncate(turn.answer),
            evaluation_summary=self._truncate(evaluation_summary, 320),
        )
        recent_turns = [*memory.recent_turns, recent_turn][-MAX_RECENT_TURNS:]

        strengths = list(memory.strengths)
        gaps = list(memory.unresolved_gaps)
        misconceptions = list(memory.misconceptions)

        # confidence=0 is the deliberate fallback signal from Commit 7. It must
        # not become remembered candidate evidence either.
        if evaluation is not None and evaluation.confidence > 0:
            day_prefix = f"Day {question.day}: "

            if evaluation.average_score >= 3.4 and not evaluation.missing_concepts and not evaluation.misconceptions:
                # Strong later evidence on the same day can close earlier gaps
                # from that day without pretending unrelated gaps disappeared.
                gaps = [item for item in gaps if not item.startswith(day_prefix)]
                misconceptions = [
                    item for item in misconceptions if not item.startswith(day_prefix)
                ]

            for point in evaluation.strong_points:
                self._append_unique(
                    strengths,
                    f"{day_prefix}{point}",
                    MAX_MEMORY_ITEMS,
                )
            for gap in evaluation.missing_concepts:
                self._append_unique(
                    gaps,
                    f"{day_prefix}{gap}",
                    MAX_MEMORY_ITEMS,
                )
            for misconception in evaluation.misconceptions:
                self._append_unique(
                    misconceptions,
                    f"{day_prefix}{misconception}",
                    MAX_MEMORY_ITEMS,
                )

        days_discussed = list(memory.days_discussed)
        if question.day not in days_discussed:
            days_discussed.append(question.day)

        updated = InterviewMemory(
            recent_turns=recent_turns,
            strengths=strengths[-MAX_MEMORY_ITEMS:],
            unresolved_gaps=gaps[-MAX_MEMORY_ITEMS:],
            misconceptions=misconceptions[-MAX_MEMORY_ITEMS:],
            days_discussed=days_discussed,
            last_updated_turn_count=answered_turn_count,
        )
        updated.rolling_summary = self._build_summary(updated, knowledge_map)
        return updated

    def render_context(
        self,
        memory: InterviewMemory | None,
        knowledge_map: CandidateKnowledgeMap | None = None,
    ) -> str:
        if memory is None:
            return "No prior interview context is available yet."

        lines = [
            "WORKING INTERVIEW MEMORY (private interviewer context; never reveal internal scores):",
            f"Rolling summary: {memory.rolling_summary}",
        ]

        if memory.strengths:
            lines.append("Observed strengths: " + " | ".join(memory.strengths[-5:]))
        if memory.unresolved_gaps:
            lines.append("Open gaps: " + " | ".join(memory.unresolved_gaps[-5:]))
        if memory.misconceptions:
            lines.append("Observed misconceptions: " + " | ".join(memory.misconceptions[-5:]))

        if knowledge_map is not None:
            topic_lines = []
            for mastery in knowledge_map.topics.values():
                if mastery.confidence <= 0:
                    continue
                topic_lines.append(
                    f"{mastery.topic.value}: {mastery.score:.0f}/100, confidence {mastery.confidence:.2f}"
                )
            if topic_lines:
                lines.append("Knowledge snapshot: " + " | ".join(topic_lines))

        if memory.recent_turns:
            lines.append("Recent turns (oldest to newest):")
            for item in memory.recent_turns:
                lines.extend(
                    [
                        f"- {item.question_id} / Day {item.day}",
                        f"  Q: {item.question}",
                        f"  A: {item.answer or '[empty answer]'}",
                        f"  Eval: {item.evaluation_summary}",
                    ]
                )

        rendered = "\n".join(lines)
        if len(rendered) <= MAX_CONTEXT_CHARS:
            return rendered
        return rendered[-MAX_CONTEXT_CHARS:]

    def _build_summary(
        self,
        memory: InterviewMemory,
        knowledge_map: CandidateKnowledgeMap | None,
    ) -> str:
        pieces = [
            f"{memory.last_updated_turn_count} answer(s) recorded",
            (
                "days discussed: " + ", ".join(str(day) for day in memory.days_discussed)
                if memory.days_discussed
                else "no curriculum days discussed yet"
            ),
        ]

        if memory.strengths:
            pieces.append("recent strength: " + memory.strengths[-1])
        if memory.unresolved_gaps:
            pieces.append("current gap: " + memory.unresolved_gaps[-1])
        if memory.misconceptions:
            pieces.append("misconception to watch: " + memory.misconceptions[-1])

        if knowledge_map is not None:
            measured = [
                mastery
                for mastery in knowledge_map.topics.values()
                if mastery.confidence > 0
            ]
            if measured:
                strongest = max(measured, key=lambda item: item.score)
                weakest = min(measured, key=lambda item: item.score)
                pieces.append(
                    f"measured topic range: strongest {strongest.topic.value} {strongest.score:.0f}, "
                    f"weakest {weakest.topic.value} {weakest.score:.0f}"
                )

        return self._truncate("; ".join(pieces) + ".", 1200)

    @staticmethod
    def _evaluation_summary(turn: InterviewTurn) -> str:
        evaluation = turn.evaluation
        if evaluation is None:
            return "No structured evaluation stored."
        if evaluation.confidence <= 0:
            return "Evaluation unavailable; no reliable evidence stored."
        return (
            f"avg {evaluation.average_score:.1f}/4; action {evaluation.recommended_action.value}; "
            f"strengths={evaluation.strong_points}; gaps={evaluation.missing_concepts}; "
            f"misconceptions={evaluation.misconceptions}"
        )

    @staticmethod
    def _append_unique(target: list[str], value: str, limit: int) -> None:
        if value in target:
            return
        target.append(value)
        if len(target) > limit:
            del target[:-limit]

    @staticmethod
    def _truncate(value: str, limit: int = MAX_TEXT_FIELD_CHARS) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(0, limit - 1)].rstrip() + "…"
