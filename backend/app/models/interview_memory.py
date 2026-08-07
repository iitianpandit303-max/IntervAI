from pydantic import BaseModel, Field


class MemoryTurn(BaseModel):
    question_id: str
    day: int
    question: str
    answer: str
    evaluation_summary: str


class InterviewMemory(BaseModel):
    """Compact working memory used for LLM context.

    Full transcript remains in InterviewSession.turns. This object intentionally
    stores only bounded, high-signal context so prompts do not grow without
    limit as the interview continues.
    """

    rolling_summary: str = "No interview answers have been recorded yet."
    recent_turns: list[MemoryTurn] = Field(default_factory=list, max_length=4)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    unresolved_gaps: list[str] = Field(default_factory=list, max_length=8)
    misconceptions: list[str] = Field(default_factory=list, max_length=8)
    days_discussed: list[int] = Field(default_factory=list, max_length=31)
    last_updated_turn_count: int = Field(default=0, ge=0)
