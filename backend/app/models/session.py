from enum import Enum

from pydantic import BaseModel, Field

from app.models.answer_evaluation import AnswerEvaluation, RecommendedAction
from app.models.candidate import CandidateProfile
from app.models.candidate_intelligence import StartingDifficulty
from app.models.interview_plan import QuestionType
from app.models.interview_memory import InterviewMemory
from app.models.knowledge_map import CandidateKnowledgeMap
from app.models.pressure import PressureChallengeType


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
    adaptive_action: RecommendedAction | None = None
    adaptive_from_question_id: str | None = None
    pressure_challenge_type: PressureChallengeType | None = None


class InterviewTurn(BaseModel):
    question_id: str
    question: str
    answer: str
    evaluation: AnswerEvaluation | None = None


class InterviewSession(BaseModel):
    session_id: str
    candidate: CandidateProfile
    questions: list[PlannedQuestion]
    turns: list[InterviewTurn] = Field(default_factory=list)
    current_index: int = 0
    adaptive_followups_used: int = 0
    pressure_followups_used: int = 0
    knowledge_map: CandidateKnowledgeMap | None = None
    memory: InterviewMemory | None = None
    done: bool = False
