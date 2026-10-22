from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


RESULT_KINDS = ("retrieval", "analysis", "direction")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    """把会话、发言、事件和三份研究结果保存在 SQLite。"""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS session (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    run_started_at TEXT
                );
                CREATE TABLE IF NOT EXISTS session_message (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS session_event (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    seq_no INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS session_result (
                    session_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(session_id, kind),
                    FOREIGN KEY(session_id) REFERENCES session(id) ON DELETE CASCADE
                );
                """
            )

    def create(self, title: str = "新会话") -> dict[str, Any]:
        now = utc_now()
        session_key = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session (id, title, status, created_at, updated_at, run_started_at)
                VALUES (?, ?, 'idle', ?, ?, NULL)
                """,
                (session_key, title, now, now),
            )
        return self.get(session_key)

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, title, status, updated_at FROM session ORDER BY updated_at DESC"
            ).fetchall()
        return [
            {"session_key": row["id"], "title": row["title"], "status": row["status"], "updated_at": row["updated_at"]}
            for row in rows
        ]

    def get(self, session_key: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM session WHERE id = ?", (session_key,)).fetchone()
            if row is None:
                raise KeyError(session_key)
            messages = connection.execute(
                """
                SELECT role, content, created_at FROM session_message
                WHERE session_id = ? ORDER BY created_at ASC, rowid ASC
                """,
                (session_key,),
            ).fetchall()
            events = connection.execute(
                """
                SELECT run_id, event_type, payload, created_at, seq_no FROM session_event
                WHERE session_id = ? ORDER BY seq_no ASC
                """,
                (session_key,),
            ).fetchall()
            results = connection.execute(
                "SELECT kind, payload FROM session_result WHERE session_id = ?",
                (session_key,),
            ).fetchall()
        stored = {item["kind"]: json.loads(item["payload"]) for item in results}
        return {
            "session_key": row["id"],
            "title": row["title"],
            "status": row["status"],
            "run_started_at": row["run_started_at"],
            "messages": [dict(item) for item in messages],
            "final_answers": [dict(item) for item in messages if item["role"] == "assistant"],
            "events": [
                {
                    "run_id": item["run_id"],
                    "type": item["event_type"],
                    "payload": json.loads(item["payload"]),
                    "created_at": item["created_at"],
                    "seq_no": item["seq_no"],
                }
                for item in events
            ],
            "results": {kind: stored.get(kind) for kind in RESULT_KINDS},
        }

    def delete(self, session_key: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM session WHERE id = ?", (session_key,))
            if cursor.rowcount == 0:
                raise KeyError(session_key)

    def append_message(self, session_key: str, role: str, content: str) -> None:
        self._require(session_key)
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO session_message (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, session_key, role, content, now),
            )
            connection.execute("UPDATE session SET updated_at = ? WHERE id = ?", (now, session_key))

    def append_event(self, session_key: str, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self._require(session_key)
        now = utc_now()
        with self._connect() as connection:
            seq_row = connection.execute(
                "SELECT COALESCE(MAX(seq_no), 0) + 1 AS next_seq FROM session_event WHERE session_id = ?",
                (session_key,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO session_event (id, session_id, run_id, event_type, payload, created_at, seq_no)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (uuid.uuid4().hex, session_key, run_id, event_type, json.dumps(payload, ensure_ascii=False), now, seq_row["next_seq"]),
            )

    def save_result(self, session_key: str, kind: str, payload: dict[str, Any]) -> None:
        if kind not in RESULT_KINDS:
            raise ValueError(f"未知研究结果：{kind}")
        self._require(session_key)
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_result (session_id, kind, payload, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, kind) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (session_key, kind, json.dumps(payload, ensure_ascii=False), now),
            )

    def clear_result(self, session_key: str, kind: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM session_result WHERE session_id = ? AND kind = ?",
                (session_key, kind),
            )

    def mark_running(self, session_key: str, started_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE session SET status = 'running', run_started_at = ?, updated_at = ? WHERE id = ?",
                (started_at, started_at, session_key),
            )

    def finish(self, session_key: str, status: str) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                "UPDATE session SET status = ?, run_started_at = NULL, updated_at = ? WHERE id = ?",
                (status, now, session_key),
            )

    def is_running(self, session_key: str) -> bool:
        record = self.get(session_key)
        return record["status"] == "running" or bool(record["run_started_at"])

    def recover_interrupted(self) -> list[str]:
        """解除重启前残留的运行锁，保留已经写入的发言和结果。"""

        recovered: list[str] = []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM session WHERE status = 'running' OR run_started_at IS NOT NULL"
            ).fetchall()
        for row in rows:
            session_key = row["id"]
            self.finish(session_key, "interrupted")
            self.append_event(session_key, "", "run.interrupted", {"message": "进程重启，运行已中断"})
            recovered.append(session_key)
        return recovered

    def _require(self, session_key: str) -> None:
        with self._connect() as connection:
            row = connection.execute("SELECT 1 FROM session WHERE id = ?", (session_key,)).fetchone()
        if row is None:
            raise KeyError(session_key)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
