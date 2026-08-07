from enum import Enum


class PressureChallengeType(str, Enum):
    """The interviewer stance used to challenge a strong engineering answer."""

    ASSUMPTION = "assumption"
    ALTERNATIVE = "alternative"
    COUNTERFACTUAL = "counterfactual"
    CONSTRAINT = "constraint"
