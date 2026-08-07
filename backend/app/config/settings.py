import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_SESSION_DB_PATH = ROOT_DIR / "backend" / "intervai_sessions.db"


def _parse_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class RuntimeSettings:
    """Deployment-facing settings that do not affect evaluator semantics."""

    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    session_db_path: Path = DEFAULT_SESSION_DB_PATH

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        configured = _parse_csv(os.getenv("INTERVAI_CORS_ORIGINS"))
        db_raw = os.getenv("INTERVAI_SESSION_DB_PATH", "").strip()
        db_path = Path(db_raw).expanduser() if db_raw else DEFAULT_SESSION_DB_PATH
        return cls(
            cors_origins=configured or DEFAULT_CORS_ORIGINS,
            session_db_path=db_path,
        )


@dataclass(frozen=True)
class LLMSettings:
    """Environment-driven configuration for an OpenAI-compatible chat API."""

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 20.0
    max_retries: int = 1

    @property
    def enabled(self) -> bool:
        return bool(self.base_url.strip() and self.api_key.strip() and self.model.strip())

    @classmethod
    def from_env(cls) -> "LLMSettings":
        timeout_raw = os.getenv("INTERVAI_LLM_TIMEOUT_SECONDS", "20")
        retries_raw = os.getenv("INTERVAI_LLM_MAX_RETRIES", "1")

        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 20.0

        try:
            retries = int(retries_raw)
        except ValueError:
            retries = 1

        return cls(
            base_url=os.getenv("INTERVAI_LLM_BASE_URL", "").rstrip("/"),
            api_key=os.getenv("INTERVAI_LLM_API_KEY", ""),
            model=os.getenv("INTERVAI_LLM_MODEL", ""),
            timeout_seconds=max(1.0, timeout),
            # A bounded retry budget prevents a transient 5xx from ruining a turn
            # without allowing provider outages to multiply judge latency.
            max_retries=min(2, max(0, retries)),
        )
