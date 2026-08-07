from enum import Enum

from pydantic import BaseModel, Field


class KnowledgeTopic(str, Enum):
    RAG = "RAG"
    VECTOR_DATABASES = "Vector Databases"
    PROMPT_ENGINEERING = "Prompt Engineering"
    AGENTIC_AI = "Agentic AI"
    MCP = "MCP"
    DEPLOYMENT = "Deployment"
    PRODUCTION_AI_SYSTEMS = "Production AI Systems"


class TopicMastery(BaseModel):
    topic: KnowledgeTopic
    score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    prior_score: float | None = Field(default=None, ge=0.0, le=100.0)
    prior_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    interview_evidence_weight: float = Field(default=0.0, ge=0.0)
    questions_asked: int = Field(default=0, ge=0)
    related_days: list[int]
    profile_evidence: list[str] = Field(default_factory=list, max_length=8)
    strong_evidence: list[str] = Field(default_factory=list, max_length=12)
    weak_evidence: list[str] = Field(default_factory=list, max_length=12)
    misconceptions: list[str] = Field(default_factory=list, max_length=12)
    last_updated_question_id: str | None = None


class CandidateKnowledgeMap(BaseModel):
    candidate_id: str
    topics: dict[str, TopicMastery]
