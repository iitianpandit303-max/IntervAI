from enum import Enum

from pydantic import BaseModel, Field


class RecommendedAction(str, Enum):
    PROBE = "PROBE"
    DEEPEN = "DEEPEN"
    PRESSURE = "PRESSURE"
    SWITCH = "SWITCH"
    RECOVER = "RECOVER"


class EvaluationSource(str, Enum):
    LLM = "llm"
    FALLBACK = "fallback"
    RULE = "rule"


class AnswerEvaluation(BaseModel):
    """Structured evidence captured from one candidate answer.

    Scores use a deliberately small 0–4 rubric so later adaptive logic can make
    stable decisions without pretending the model has exam-level precision.
    """

    technical_accuracy: int = Field(ge=0, le=4)
    conceptual_understanding: int = Field(ge=0, le=4)
    engineering_reasoning: int = Field(ge=0, le=4)
    implementation_depth: int = Field(ge=0, le=4)
    communication_clarity: int = Field(ge=0, le=4)

    strong_points: list[str] = Field(default_factory=list, max_length=5)
    missing_concepts: list[str] = Field(default_factory=list, max_length=5)
    misconceptions: list[str] = Field(default_factory=list, max_length=5)

    recommended_action: RecommendedAction
    confidence: float = Field(ge=0.0, le=1.0)
    evaluator_rationale: str = Field(min_length=5, max_length=1000)
    source: EvaluationSource = EvaluationSource.LLM

    @property
    def average_score(self) -> float:
        scores = [
            self.technical_accuracy,
            self.conceptual_understanding,
            self.engineering_reasoning,
            self.implementation_depth,
            self.communication_clarity,
        ]
        return sum(scores) / len(scores)
