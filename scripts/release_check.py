"""Run the final IntervAI release checks from one command.

Examples:
    python scripts/release_check.py
    python scripts/release_check.py --base-url https://your-api.example.com
    python scripts/release_check.py --skip-frontend

The public smoke test is optional until a backend URL exists.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str], cwd: Path) -> None:
    print(f"\n== {label} ==")
    print("$", " ".join(command))
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(f"{label} FAILED with exit code {completed.returncode}.")
    print(f"{label}: PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IntervAI release checks.")
    parser.add_argument("--base-url", help="Optional deployed backend origin to smoke-test.")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        run(
            "Backend tests",
            [sys.executable, "-m", "pytest", "-q"],
            ROOT / "backend",
        )

    if not args.skip_frontend:
        npm = shutil.which("npm")
        if not npm:
            raise SystemExit(
                "Frontend build FAILED: npm was not found. "
                "Install Node/npm or rerun with --skip-frontend."
            )
        run("Frontend production build", [npm, "run", "build"], ROOT / "frontend")

    if args.base_url:
        run(
            "Public evaluator smoke test",
            [
                sys.executable,
                str(ROOT / "scripts" / "judge_smoke_test.py"),
                "--base-url",
                args.base_url,
            ],
            ROOT,
        )

    print("\nRELEASE CHECK PASS")
    if not args.base_url:
        print("Note: no --base-url supplied, so the public deployment smoke test was skipped.")


if __name__ == "__main__":
    main()
