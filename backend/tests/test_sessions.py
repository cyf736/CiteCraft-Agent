from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.repositories.sessions.sqlite import SessionStore


EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "settings.example.json"


def test_sqlite_keeps_messages_answers_events_and_results(tmp_path: Path) -> None:
    database = tmp_path / "sessions.sqlite3"
    store = SessionStore(database)
    first = store.create("第一份")
    other = store.create("另一份")
    store.append_message(first["session_key"], "user", "原始问题")
    store.append_message(first["session_key"], "assistant", "最终回答")
    store.append_event(first["session_key"], "run-1", "run.completed", {"answer": "最终回答"})
    store.save_result(first["session_key"], "retrieval", {"query": "原始问题"})
    store.save_result(first["session_key"], "analysis", {"summary": "分析"})
    store.save_result(first["session_key"], "direction", {"routes": ["路线"]})

    reopened = SessionStore(database)
    loaded = reopened.get(first["session_key"])
    assert [item["content"] for item in loaded["messages"]] == ["原始问题", "最终回答"]
    assert loaded["final_answers"][0]["content"] == "最终回答"
    assert loaded["events"][0]["type"] == "run.completed"
    assert loaded["results"] == {
        "retrieval": {"query": "原始问题"},
        "analysis": {"summary": "分析"},
        "direction": {"routes": ["路线"]},
    }
    isolated = reopened.get(other["session_key"])
    assert isolated["messages"] == []
    assert isolated["results"] == {"retrieval": None, "analysis": None, "direction": None}

    reopened.delete(first["session_key"])
    after_delete = SessionStore(database)
    assert first["session_key"] not in {item["session_key"] for item in after_delete.list_sessions()}
    try:
        after_delete.get(first["session_key"])
    except KeyError:
        missing = True
    else:
        missing = False
    assert missing


def test_http_session_crud(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    shutil.copyfile(EXAMPLE, settings)
    app = create_app(settings_path=settings, database_path=tmp_path / "sessions.sqlite3")
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "课题"})
        assert created.status_code == 201
        session_key = created.json()["session_key"]
        listed = client.get("/api/sessions")
        assert session_key in {item["session_key"] for item in listed.json()["sessions"]}

        loaded = client.get(f"/api/sessions/{session_key}")
        assert loaded.status_code == 200
        assert loaded.json()["title"] == "课题"

        deleted = client.delete(f"/api/sessions/{session_key}")
        assert deleted.status_code == 200
        missing = client.get(f"/api/sessions/{session_key}")
        assert missing.status_code == 404
        assert missing.json()["error"]["status"] == 404
        assert missing.json()["error"]["message"]
