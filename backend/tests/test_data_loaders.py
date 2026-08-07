from app.repositories.candidate_repository import CandidateRepository
from app.repositories.curriculum_repository import CurriculumRepository
from app.services.curriculum_service import CurriculumService


def test_curriculum_loads_all_31_days() -> None:
    repository = CurriculumRepository()
    curriculum = repository.get_curriculum()

    assert len(curriculum.days) == 31
    assert curriculum.cohort.startswith("AI Cohort")
    assert repository.get_day(23).title == "Model Context Protocol (MCP)"


def test_candidate_collection_loads() -> None:
    repository = CandidateRepository()

    assert len(repository.all()) == 20
    assert repository.get("CAND-001").member.name == "Sarah Johnson"


def test_candidate_curriculum_join_uses_day_number() -> None:
    candidates = CandidateRepository()
    service = CurriculumService()
    candidate = candidates.get("CAND-002")

    matched = service.curriculum_for_candidate(candidate)
    day_18 = next(day for day in matched if day.day == 18)

    # Candidate title is shorter than the curriculum title; day number still joins safely.
    assert day_18.title == "Full-Stack Integration & Streaming Responses"
