from pydantic import BaseModel, Field


class CandidateMember(BaseModel):
    id: str
    name: str
    jobRole: str
    yearsExperience: int
    education: str
    status: str


class CandidateMission(BaseModel):
    day: int
    title: str
    passed: bool | None = None
    skipped: bool = False
    attempts: int | None = None


class CandidateSignals(BaseModel):
    commitDays: int
    missionsCompleted: int
    missionsFirstTry: int


class CandidateProfile(BaseModel):
    member: CandidateMember
    missions: list[CandidateMission] = Field(default_factory=list)
    signals: CandidateSignals


class CandidateCollection(BaseModel):
    candidates: list[CandidateProfile]
