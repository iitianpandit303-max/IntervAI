import json
from pathlib import Path

from app.models.curriculum import Curriculum, CurriculumDay, CurriculumModule


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CURRICULUM_PATH = ROOT_DIR / "data" / "curriculum.json"


class CurriculumRepository:
    def __init__(self, path: Path | str = DEFAULT_CURRICULUM_PATH) -> None:
        self.path = Path(path)
        self._curriculum = self._load()
        self._days_by_number = {item.day: item for item in self._curriculum.days}
        self._modules_by_number = {item.n: item for item in self._curriculum.modules}

    def _load(self) -> Curriculum:
        with self.path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return Curriculum.model_validate(payload)

    def get_curriculum(self) -> Curriculum:
        return self._curriculum

    def get_day(self, day: int) -> CurriculumDay | None:
        return self._days_by_number.get(day)

    def get_module(self, module_number: int) -> CurriculumModule | None:
        return self._modules_by_number.get(module_number)

    def all_days(self) -> list[CurriculumDay]:
        return list(self._curriculum.days)
