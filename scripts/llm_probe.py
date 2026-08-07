"""Verify that the configured OpenAI-compatible LLM can return structured JSON.

Run from the repository root after setting the INTERVAI_LLM_* variables:

    python scripts/llm_probe.py

No secret values are printed.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config.settings import LLMSettings  # noqa: E402
from app.llm.client import LLMClientError, OpenAICompatibleLLMClient  # noqa: E402


def main() -> None:
    settings = LLMSettings.from_env()
    if not settings.enabled:
        raise SystemExit(
            "LLM is not configured. Set INTERVAI_LLM_BASE_URL, "
            "INTERVAI_LLM_API_KEY and INTERVAI_LLM_MODEL first."
        )

    client = OpenAICompatibleLLMClient(settings)
    try:
        result = client.complete_json(
            system_prompt=(
                "You are a deployment probe. Return one JSON object only. "
                'The object must be exactly {"status":"ok"}.'
            ),
            user_prompt='Return exactly {"status":"ok"}.',
        )
    except LLMClientError as exc:
        raise SystemExit(f"LLM probe FAILED: {exc}") from exc

    if result.get("status") != "ok":
        raise SystemExit(f"LLM probe FAILED: unexpected structured response {result!r}")

    print(f"LLM probe PASS: model={settings.model!r}, structured JSON received.")


if __name__ == "__main__":
    main()
