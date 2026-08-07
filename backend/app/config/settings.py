import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class LLMSettings:
    """Environment-driven configuration for an OpenAI-compatible chat API."""

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 20.0

    @property
    def enabled(self) -> bool:
        return bool(self.base_url.strip() and self.api_key.strip() and self.model.strip())

    @classmethod
    def from_env(cls) -> "LLMSettings":
        timeout_raw = os.getenv("INTERVAI_LLM_TIMEOUT_SECONDS", "20")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 20.0

        return cls(
            base_url=os.getenv("INTERVAI_LLM_BASE_URL", "").rstrip("/"),
            api_key=os.getenv("INTERVAI_LLM_API_KEY", ""),
            model=os.getenv("INTERVAI_LLM_MODEL", ""),
            timeout_seconds=max(1.0, timeout),
        )
