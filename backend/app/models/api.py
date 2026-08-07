from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.candidate import CandidateProfile


class InterviewRequest(BaseModel):
    sessionId: str = Field(min_length=1)
    candidate: CandidateProfile | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_turn_shape(self) -> "InterviewRequest":
        if self.candidate is None and self.message is None:
            raise ValueError("Provide candidate to start, or message to continue an interview.")
        return self


class FeedbackPayload(BaseModel):
    summary: str
    strengths: list[str]
    gaps: list[str]
    next: list[str]


class InterviewResponse(BaseModel):
    reply: str
    done: bool
    feedback: FeedbackPayload | None = None


class ErrorResponse(BaseModel):
    detail: str
