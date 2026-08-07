from dataclasses import dataclass

from app.models.answer_evaluation import AnswerEvaluation, RecommendedAction
from app.models.session import InterviewSession, PlannedQuestion


MAX_ADAPTIVE_FOLLOWUPS = 2
MAX_PRESSURE_FOLLOWUPS = 2
MIN_ADAPTATION_CONFIDENCE = 0.5
MIN_PRESSURE_CONFIDENCE = 0.75
MIN_PRESSURE_AVERAGE = 3.2
MIN_PRESSURE_REASONING = 3


@dataclass(frozen=True)
class AdaptationDecision:
    action: RecommendedAction
    should_insert_followup: bool
    reason: str


class AdaptivePolicy:
    """Converts evaluation evidence into a bounded next-turn decision.

    The model's recommended action is advisory. Backend rules normalize it using
    score, confidence, concrete gaps and pressure eligibility. Pressure Mode is
    only allowed for strong, high-confidence answers where the evaluator found a
    concrete engineering choice worth defending. All inserted questions share a
    global budget so adaptation can never grow the interview without bound.
    """

    max_followups = MAX_ADAPTIVE_FOLLOWUPS
    max_pressure_followups = MAX_PRESSURE_FOLLOWUPS
    min_confidence = MIN_ADAPTATION_CONFIDENCE
    min_pressure_confidence = MIN_PRESSURE_CONFIDENCE
    min_pressure_average = MIN_PRESSURE_AVERAGE
    min_pressure_reasoning = MIN_PRESSURE_REASONING

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
            return self._switch("Avoid chaining multiple adaptive questions from one probe or challenge.")

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

        if self._pressure_eligible(session=session, evaluation=evaluation):
            return AdaptationDecision(
                action=RecommendedAction.PRESSURE,
                should_insert_followup=True,
                reason=(
                    "Strong, high-confidence evidence contains an engineering choice "
                    "that is suitable for an assumption or trade-off challenge."
                ),
            )

        if evaluation.recommended_action is RecommendedAction.DEEPEN or average >= 3.4:
            return AdaptationDecision(
                action=RecommendedAction.DEEPEN,
                should_insert_followup=True,
                reason="Strong evidence supports a deeper technical follow-up.",
            )

        return self._switch("Enough evidence was gathered; continue the planned curriculum coverage.")

    def _pressure_eligible(
        self,
        *,
        session: InterviewSession,
        evaluation: AnswerEvaluation,
    ) -> bool:
        return (
            evaluation.recommended_action is RecommendedAction.PRESSURE
            and evaluation.confidence >= self.min_pressure_confidence
            and evaluation.average_score >= self.min_pressure_average
            and evaluation.engineering_reasoning >= self.min_pressure_reasoning
            and session.pressure_followups_used < self.max_pressure_followups
        )

    @staticmethod
    def _switch(reason: str) -> AdaptationDecision:
        return AdaptationDecision(
            action=RecommendedAction.SWITCH,
            should_insert_followup=False,
            reason=reason,
        )
