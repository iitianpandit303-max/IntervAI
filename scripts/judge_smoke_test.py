"""Run the public evaluator flow against a live IntervAI deployment.

Usage:
    python scripts/judge_smoke_test.py --base-url http://127.0.0.1:8000
    python scripts/judge_smoke_test.py --base-url https://api.example.com --candidate CAND-010

This script intentionally uses only Python's standard library so it can run from
any machine without installing the backend dependencies.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data" / "candidates.json"


def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


def load_candidate(candidate_id: str) -> dict[str, Any]:
    payload = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    for candidate in payload["candidates"]:
        if candidate["member"]["id"] == candidate_id:
            return candidate
    raise SystemExit(f"Candidate {candidate_id!r} was not found in {CANDIDATES_PATH}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the IntervAI evaluator contract.")
    parser.add_argument("--base-url", required=True, help="Backend origin, without /api/interview")
    parser.add_argument("--candidate", default="CAND-001")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    endpoint = f"{base_url}/api/interview"
    session_id = f"smoke-{uuid.uuid4()}"
    candidate = load_candidate(args.candidate)

    health_status, health = request_json(f"{base_url}/health")
    if health_status != 200 or health.get("status") != "ok":
        raise SystemExit(f"Health check failed: {health}")
    print(f"health: OK ({health.get('llmMode', 'unknown mode')})")

    status, started = request_json(
        endpoint,
        method="POST",
        payload={"sessionId": session_id, "candidate": candidate},
    )
    if status != 200 or started.get("done") is not False or set(started) != {"reply", "done"}:
        raise SystemExit(f"Start contract failed: {started}")
    print(f"start: OK ({args.candidate}, session={session_id})")

    final = None
    for turn in range(1, 13):
        _, response = request_json(
            endpoint,
            method="POST",
            payload={
                "sessionId": session_id,
                "message": (
                    "I would explain the concept, make the engineering trade-off explicit, "
                    "describe the implementation, and validate the result with measurable tests. "
                    f"This is smoke-test answer {turn}."
                ),
            },
        )
        print(f"turn {turn}: {'DONE' if response.get('done') else 'OK'}")
        if response.get("done"):
            final = response
            break

    if final is None:
        raise SystemExit("Interview did not complete within the bounded 12-turn smoke-test window.")

    required_feedback = {"summary", "strengths", "gaps", "next"}
    if set(final) != {"reply", "done", "feedback"} or set(final["feedback"]) != required_feedback:
        raise SystemExit(f"Final response contract failed: {final}")

    query = urlencode({"sessionId": session_id})
    _, insights = request_json(f"{endpoint}?{query}")
    if insights.get("answeredQuestions", 0) < 8:
        raise SystemExit(f"Minimum question count failed: {insights}")
    if len(insights.get("curriculumDaysCovered", [])) < 4:
        raise SystemExit(f"Minimum curriculum coverage failed: {insights}")

    print(
        "PASS: exact evaluator flow completed with "
        f"{insights['answeredQuestions']} answers across "
        f"{len(insights['curriculumDaysCovered'])} curriculum days."
    )


if __name__ == "__main__":
    main()
