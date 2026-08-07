import json
import sqlite3
from pathlib import Path

from app.models.session import InterviewSession


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT_DIR / "backend" / "intervai_sessions.db"


class SessionRepository:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def exists(self, session_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM interview_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row is not None

    def get(self, session_id: str) -> InterviewSession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM interview_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if row is None:
            return None
        return InterviewSession.model_validate(json.loads(row["payload"]))

    def save(self, session: InterviewSession) -> None:
        payload = session.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO interview_sessions (session_id, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session.session_id, payload),
            )

    def delete(self, session_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM interview_sessions WHERE session_id = ?",
                (session_id,),
            )
