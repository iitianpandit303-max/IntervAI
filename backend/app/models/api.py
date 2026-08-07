from pydantic import BaseModel, Field, model_validator

from app.models.candidate import CandidateProfile


class InterviewRequest(BaseModel):
    sessionId: str = Field(min_length=1)
    candidate: CandidateProfile | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_turn_shape(self) -> "InterviewRequest":
        has_candidate = self.candidate is not None
        has_message = self.message is not None
        if has_candidate == has_message:
            raise ValueError(
                "Provide exactly one of candidate (start) or message (conversation turn)."
            )
        if not self.sessionId.strip():
            raise ValueError("sessionId must contain a non-whitespace value.")
        self.sessionId = self.sessionId.strip()
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
