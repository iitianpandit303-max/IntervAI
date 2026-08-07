from enum import Enum

from pydantic import BaseModel, Field


class ReadinessLevel(str, Enum):
    NEEDS_FOUNDATION = "Needs Foundation"
    DEVELOPING = "Developing"
    INTERVIEW_READY = "Interview Ready"
    STRONG = "Strong"


class StruggledQuestion(BaseModel):
    question_id: str
    day: int
    question: str
    score: float = Field(ge=0.0, le=100.0)
    reason: str


class InterviewReadinessReport(BaseModel):
    """Rich internal report kept in session state.

    The evaluator-facing API still returns only the four fields mandated by the
    technical specification. Keeping this richer object internally lets the
    frontend render a useful report later without weakening the external
    contract.
    """

    overall_score: float = Field(ge=0.0, le=100.0)
    readiness_level: ReadinessLevel
    report_confidence: float = Field(ge=0.0, le=1.0)

    answered_questions: int = Field(ge=0)
    curriculum_days_covered: list[int]
    adaptive_followups_used: int = Field(default=0, ge=0)
    pressure_challenges_used: int = Field(default=0, ge=0)

    technical_accuracy: float = Field(ge=0.0, le=100.0)
    conceptual_understanding: float = Field(ge=0.0, le=100.0)
    engineering_reasoning: float = Field(ge=0.0, le=100.0)
    communication_quality: float = Field(ge=0.0, le=100.0)
    answer_depth: float = Field(ge=0.0, le=100.0)

    strongest_topics: list[str] = Field(default_factory=list, max_length=4)
    weakest_topics: list[str] = Field(default_factory=list, max_length=4)
    topics_to_revise: list[str] = Field(default_factory=list, max_length=6)
    curriculum_days_to_revisit: list[int] = Field(default_factory=list, max_length=6)
    struggled_questions: list[StruggledQuestion] = Field(default_factory=list, max_length=6)

    strengths: list[str] = Field(default_factory=list, max_length=6)
    gaps: list[str] = Field(default_factory=list, max_length=6)
    suggested_next_steps: list[str] = Field(default_factory=list, max_length=6)
