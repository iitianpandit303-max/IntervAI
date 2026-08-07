from pydantic import BaseModel, Field

from app.models.candidate import CandidateProfile


class PlannedQuestion(BaseModel):
    question_id: str
    day: int
    title: str
    text: str


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
