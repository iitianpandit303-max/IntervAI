from app.models.candidate import CandidateProfile
from app.models.curriculum import CurriculumDay
from app.repositories.curriculum_repository import CurriculumRepository


class CurriculumService:
    """Joins candidate mission history to curriculum by day number, never title text."""

    def __init__(self, repository: CurriculumRepository | None = None) -> None:
        self.repository = repository or CurriculumRepository()

    def curriculum_for_candidate(self, candidate: CandidateProfile) -> list[CurriculumDay]:
        seen: set[int] = set()
        matched: list[CurriculumDay] = []

        for mission in candidate.missions:
            if mission.day in seen:
                continue
            day = self.repository.get_day(mission.day)
            if day is not None:
                matched.append(day)
                seen.add(mission.day)

        return matched

    def get_day(self, day: int) -> CurriculumDay | None:
        return self.repository.get_day(day)
