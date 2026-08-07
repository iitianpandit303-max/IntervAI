from pydantic import BaseModel, Field


class CurriculumModule(BaseModel):
    n: int
    title: str
    days: list[int]


class CurriculumDay(BaseModel):
    day: int
    title: str
    type: str
    tools: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)


class Curriculum(BaseModel):
    cohort: str
    modules: list[CurriculumModule]
    days: list[CurriculumDay]
