from dataclasses import dataclass

from app.models.answer_evaluation import AnswerEvaluation, RecommendedAction
from app.models.session import InterviewSession, PlannedQuestion


MAX_ADAPTIVE_FOLLOWUPS = 2
MIN_ADAPTATION_CONFIDENCE = 0.5


@dataclass(frozen=True)
class AdaptationDecision:
    action: RecommendedAction
    should_insert_followup: bool
    reason: str


class AdaptivePolicy:
    """Converts evaluation evidence into a bounded next-turn decision.

    The model's recommended action is advisory. Backend rules normalize it using
    score, confidence and concrete gaps so one noisy model decision cannot cause
    an endless follow-up chain or break the deterministic coverage plan.
    """

    max_followups = MAX_ADAPTIVE_FOLLOWUPS
    min_confidence = MIN_ADAPTATION_CONFIDENCE

    def decide(
        self,
        *,
        session: InterviewSession,
        current: PlannedQuestion,
        evaluation: AnswerEvaluation,
    ) -> AdaptationDecision:
        if evaluation.confidence < self.min_confidence:
            return self._switch("Evaluation confidence is too low to change the interview plan.")

        if session.adaptive_followups_used >= self.max_followups:
            return self._switch("Adaptive follow-up budget has been reached.")

        if current.adaptive_from_question_id is not None:
            return self._switch("Avoid chaining multiple adaptive questions from one probe.")

        average = evaluation.average_score
        has_gap = bool(evaluation.missing_concepts or evaluation.misconceptions)

        # Strong score boundaries override an inconsistent model action.
        if average <= 1.4 or evaluation.recommended_action is RecommendedAction.RECOVER:
            return AdaptationDecision(
                action=RecommendedAction.RECOVER,
                should_insert_followup=True,
                reason="Weak evidence requires a simpler diagnostic follow-up.",
            )

        if (
            average < 2.8
            or has_gap
            or evaluation.recommended_action is RecommendedAction.PROBE
        ):
            return AdaptationDecision(
                action=RecommendedAction.PROBE,
                should_insert_followup=True,
                reason="Partial evidence or a concrete gap warrants a focused probe.",
            )

        if evaluation.recommended_action in {
            RecommendedAction.DEEPEN,
            RecommendedAction.PRESSURE,
        } or average >= 3.4:
            # PRESSURE is deliberately normalized to DEEPEN in Commit 8. Commit 9
            # will introduce the actual assumption-challenging pressure behavior.
            return AdaptationDecision(
                action=RecommendedAction.DEEPEN,
                should_insert_followup=True,
                reason="Strong evidence supports a deeper technical follow-up.",
            )

        return self._switch("Enough evidence was gathered; continue the planned curriculum coverage.")

    @staticmethod
    def _switch(reason: str) -> AdaptationDecision:
        return AdaptationDecision(
            action=RecommendedAction.SWITCH,
            should_insert_followup=False,
            reason=reason,
        )
