from pydantic import BaseModel, Field

from app.models.knowledge_map import CandidateKnowledgeMap
from app.models.readiness_report import InterviewReadinessReport


class CurrentQuestionInsight(BaseModel):
    questionId: str
    day: int
    title: str
    questionType: str
    difficulty: str
    adaptiveAction: str | None = None
    pressureChallengeType: str | None = None


class InterviewInsightsResponse(BaseModel):
    """Frontend-safe read model for the existing interview route.

    The hackathon evaluator continues to use POST /api/interview exactly as
    specified. This companion GET on the same path is hidden from OpenAPI and
    only exposes presentation-safe session intelligence to the React demo.
    """

    sessionId: str
    done: bool
    answeredQuestions: int = Field(ge=0)
    plannedQuestions: int = Field(ge=0)
    curriculumDaysCovered: list[int]
    adaptiveFollowupsUsed: int = Field(ge=0)
    pressureChallengesUsed: int = Field(ge=0)
    currentQuestion: CurrentQuestionInsight | None = None
    knowledgeMap: CandidateKnowledgeMap | None = None
    finalReport: InterviewReadinessReport | None = None
