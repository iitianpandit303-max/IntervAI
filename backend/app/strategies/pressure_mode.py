from app.models.interview_plan import QuestionType
from app.models.pressure import PressureChallengeType
from app.models.session import PlannedQuestion


class PressureModeStrategy:
    """Chooses how to challenge an otherwise strong answer.

    Pressure Mode does not mean hostility. It introduces one realistic change to
    the candidate's assumptions and asks them to defend or revise the decision.
    The question's original style selects a predictable challenge shape.
    """

    def select_challenge(self, question: PlannedQuestion) -> PressureChallengeType:
        if question.question_type is QuestionType.TRADEOFF:
            return PressureChallengeType.ALTERNATIVE
        if question.question_type is QuestionType.SYSTEM_DESIGN:
            return PressureChallengeType.CONSTRAINT
        if question.question_type in {
            QuestionType.IMPLEMENTATION,
            QuestionType.DEBUGGING,
        }:
            return PressureChallengeType.COUNTERFACTUAL
        return PressureChallengeType.ASSUMPTION
