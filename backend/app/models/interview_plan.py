from enum import Enum

from pydantic import BaseModel, Field

from app.models.candidate_intelligence import StartingDifficulty


class QuestionType(str, Enum):
    CONCEPT = "concept"
    IMPLEMENTATION = "implementation"
    DEBUGGING = "debugging"
    TRADEOFF = "tradeoff"
    SYSTEM_DESIGN = "system_design"
    FOLLOW_UP = "follow_up"
    PRESSURE = "pressure"


class InterviewPlanSummary(BaseModel):
    candidate_id: str
    starting_difficulty: StartingDifficulty
    target_questions: int = Field(ge=8)
    minimum_unique_days: int = Field(ge=4)
    selected_days: list[int]
    unique_days: list[int]
