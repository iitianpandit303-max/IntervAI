import json
from pathlib import Path

from app.models.candidate import CandidateCollection, CandidateProfile


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CANDIDATES_PATH = ROOT_DIR / "data" / "candidates.json"


class CandidateRepository:
    def __init__(self, path: Path | str = DEFAULT_CANDIDATES_PATH) -> None:
        self.path = Path(path)
        self._collection = self._load()
        self._by_id = {
            candidate.member.id: candidate for candidate in self._collection.candidates
        }

    def _load(self) -> CandidateCollection:
        with self.path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return CandidateCollection.model_validate(payload)

    def all(self) -> list[CandidateProfile]:
        return list(self._collection.candidates)

    def get(self, candidate_id: str) -> CandidateProfile | None:
        return self._by_id.get(candidate_id)
