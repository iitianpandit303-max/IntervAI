import json
from typing import Any, Protocol

import httpx

from app.config.settings import LLMSettings


class LLMClientError(RuntimeError):
    pass


class LLMClient(Protocol):
    @property
    def enabled(self) -> bool: ...

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]: ...


class OpenAICompatibleLLMClient:
    """Small provider-neutral client for OpenAI-compatible chat-completions APIs.

    We intentionally use HTTP directly instead of a provider SDK so the rest of
    the interview engine is not coupled to a specific vendor during the hackathon.
    """

    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings or LLMSettings.from_env()

    @property
    def enabled(self) -> bool:
        return self.settings.enabled

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.enabled:
            raise LLMClientError("llm_not_configured")

        payload = {
            "model": self.settings.model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = httpx.post(
                f"{self.settings.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.settings.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMClientError("llm_request_failed") from exc

        if not isinstance(content, str):
            raise LLMClientError("llm_content_missing")

        try:
            parsed = json.loads(self._strip_code_fence(content))
        except json.JSONDecodeError as exc:
            raise LLMClientError("llm_invalid_json") from exc

        if not isinstance(parsed, dict):
            raise LLMClientError("llm_json_not_object")
        return parsed

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return text
