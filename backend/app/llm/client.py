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

    The interview engine remains provider independent. This client has a tiny,
    bounded retry budget for transient transport/429/5xx failures and falls back
    quickly on timeouts so a provider outage does not stall the evaluator.
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
            
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        attempts = self.settings.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
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
                return self._parse_content(content)
            except httpx.TimeoutException as exc:
                # Do not retry a full timeout: deterministic fallback is safer
                # than doubling judge latency.
                raise LLMClientError("llm_request_timed_out") from exc
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                retryable = status == 429 or status >= 500
                if retryable and attempt < attempts - 1:
                    continue
                raise LLMClientError("llm_request_failed") from exc
            except httpx.TransportError as exc:
                last_error = exc
                if attempt < attempts - 1:
                    continue
                raise LLMClientError("llm_request_failed") from exc
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise LLMClientError("llm_content_missing") from exc

        raise LLMClientError("llm_request_failed") from last_error

    @classmethod
    def _parse_content(cls, content: Any) -> dict[str, Any]:
        if not isinstance(content, str):
            raise LLMClientError("llm_content_missing")

        text = cls._strip_code_fence(content)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Some OpenAI-compatible providers occasionally prepend a short
            # sentence despite a JSON-only prompt. Recover a single JSON object
            # when it is unambiguous; otherwise fall back safely.
            first = text.find("{")
            last = text.rfind("}")
            if first < 0 or last <= first:
                raise LLMClientError("llm_invalid_json")
            try:
                parsed = json.loads(text[first : last + 1])
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
