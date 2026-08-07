from pydantic import BaseModel, Field


class GeneratedQuestionPayload(BaseModel):
    question: str = Field(min_length=15, max_length=1200)
    rationale: str = Field(min_length=5, max_length=800)
