from enum import Enum

from pydantic import BaseModel, Field

from app.models.candidate import CandidateProfile
from app.models.candidate_intelligence import StartingDifficulty
from app.models.interview_plan import QuestionType


class QuestionGenerationSource(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    FALLBACK = "fallback"


class PlannedQuestion(BaseModel):
    question_id: str
    day: int
    title: str
    text: str
    question_type: QuestionType = QuestionType.CONCEPT
    difficulty: StartingDifficulty = StartingDifficulty.INTERMEDIATE
    purpose: str = "curriculum coverage"
    source_objective: str | None = None
    generation_source: QuestionGenerationSource = QuestionGenerationSource.DETERMINISTIC
    generation_rationale: str | None = None


class InterviewTurn(BaseModel):
    question_id: str
    question: str
    answer: str


class InterviewSession(BaseModel):
    session_id: str
    candidate: CandidateProfile
    questions: list[PlannedQuestion]
    turns: list[InterviewTurn] = Field(default_factory=list)
    current_index: int = 0
    done: bool = False
