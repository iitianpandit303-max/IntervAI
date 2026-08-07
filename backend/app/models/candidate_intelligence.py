from enum import Enum

from pydantic import BaseModel, Field


class LearningState(str, Enum):
    STRONG = "strong"
    DEVELOPING = "developing"
    DIAGNOSTIC = "diagnostic"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class StartingDifficulty(str, Enum):
    FOUNDATION = "foundation"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class DayLearningSignal(BaseModel):
    day: int
    title: str
    state: LearningState
    attempts: int | None = None
    interview_priority: float = Field(ge=0.0, le=1.0)
    prior_mastery: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: str


class CandidateIntelligence(BaseModel):
    candidate_id: str
    candidate_name: str
    starting_difficulty: StartingDifficulty
    profile_confidence: float = Field(ge=0.0, le=1.0)
    completion_rate: float = Field(ge=0.0, le=1.0)
    first_try_rate: float = Field(ge=0.0, le=1.0)
    commit_consistency: float = Field(ge=0.0, le=1.0)
    day_signals: list[DayLearningSignal]
    strong_days: list[int]
    diagnostic_days: list[int]
    failed_days: list[int]
    skipped_days: list[int]
    unknown_days: list[int]
    priority_days: list[int]
