from __future__ import annotations

import asyncio
import json
import shutil
import threading
from pathlib import Path

import httpx

from src.api.app import create_app
from src.repositories.sessions.sqlite import SessionStore
from src.services.session_runs import RunContext


EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "settings.example.json"


def _settings(tmp_path: Path) -> Path:
    target = tmp_path / "settings.json"
    shutil.copyfile(EXAMPLE, target)
    return target


async def _read_stream(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    async with client.stream("GET", url) as response:
        chunks: list[str] = []
        async for chunk in response.aiter_text():
            chunks.append(chunk)
            if "stream closed" in "".join(chunks):
                break
        return response.headers["content-type"], "".join(chunks)


def _events(body: str) -> list[dict]:
    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line.removeprefix("data: ")))
    return events


def test_run_stream_is_ordered_and_rejects_a_second_submission(tmp_path: Path) -> None:
    gate = threading.Event()

    async def handler(context: RunContext) -> None:
        await context.emit({"type": "worker.completed", "step": "first"})
        await asyncio.to_thread(gate.wait)
        await context.emit({"type": "run.completed", "answer": "最终回答"})

    async def scenario() -> None:
        app = create_app(
            settings_path=_settings(tmp_path),
            database_path=tmp_path / "sessions.sqlite3",
            run_handler=handler,
            heartbeat_interval=0.05,
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/sessions", json={"title": "课题"})
            session_key = created.json()["session_key"]
            app.state.sessions.save_result(session_key, "retrieval", {"query": "已有结果"})
            started = await client.post(f"/api/sessions/{session_key}/runs", json={"content": "问题"})
            assert started.status_code == 202
            payload = started.json()
            assert payload["run_id"]
            assert payload["stream_url"] == f"/api/sessions/{session_key}/runs/{payload['run_id']}/stream"
            for _ in range(50):
                current = app.state.sessions.get(session_key)
                if any(item["type"] == "worker.completed" for item in current["events"]):
                    break
                await asyncio.sleep(0.02)
            else:
                raise AssertionError("运行没有开始")
            blocked = await client.post(f"/api/sessions/{session_key}/runs", json={"content": "第二轮"})
            assert blocked.status_code == 409
            assert blocked.json()["error"]["status"] == 409
            loaded = await client.get(f"/api/sessions/{session_key}")
            assert loaded.json()["results"]["retrieval"] == {"query": "已有结果"}
            assert [item["content"] for item in loaded.json()["messages"] if item["role"] == "user"] == ["问题"]
            gate.set()
            content_type, body = await _read_stream(client, payload["stream_url"])
            assert content_type.startswith("text/event-stream")
            assert [item["type"] for item in _events(body)] == ["worker.completed", "run.completed"]

    asyncio.run(scenario())


def test_waiting_emits_a_comment_heartbeat(tmp_path: Path) -> None:
    async def handler(context: RunContext) -> None:
        await asyncio.sleep(0.2)
        await context.emit({"type": "worker.completed"})

    async def scenario() -> None:
        app = create_app(
            settings_path=_settings(tmp_path),
            database_path=tmp_path / "sessions.sqlite3",
            run_handler=handler,
            heartbeat_interval=0.05,
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/sessions", json={})
            session_key = created.json()["session_key"]
            started = await client.post(f"/api/sessions/{session_key}/runs", json={"content": "问题"})
            _, body = await _read_stream(client, started.json()["stream_url"])
            loaded = await client.get(f"/api/sessions/{session_key}")
            assert ": heartbeat" in body
            assert loaded.json()["results"] == {"retrieval": None, "analysis": None, "direction": None}
            assert loaded.json()["final_answers"] == []

    asyncio.run(scenario())


def test_missing_session_and_unregistered_handler(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = create_app(
            settings_path=_settings(tmp_path),
            database_path=tmp_path / "sessions.sqlite3",
            heartbeat_interval=0.05,
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            missing = await client.post("/api/sessions/missing/runs", json={"content": "问题"})
            assert missing.status_code == 404
            assert missing.json()["error"]["message"]
            assert missing.json()["error"]["status"] == 404

            created = await client.post("/api/sessions", json={})
            session_key = created.json()["session_key"]
            started = await client.post(f"/api/sessions/{session_key}/runs", json={"content": "问题"})
            _, body = await _read_stream(client, started.json()["stream_url"])
            loaded = await client.get(f"/api/sessions/{session_key}")
            assert _events(body)[-1]["type"] == "run.failed"
            assert loaded.json()["results"] == {"retrieval": None, "analysis": None, "direction": None}
            assert loaded.json()["final_answers"] == []
            assert "最终回答" not in body

    asyncio.run(scenario())


def test_cancel_ends_the_stream(tmp_path: Path) -> None:
    async def handler(context: RunContext) -> None:
        await asyncio.sleep(30)

    async def scenario() -> None:
        app = create_app(
            settings_path=_settings(tmp_path),
            database_path=tmp_path / "sessions.sqlite3",
            run_handler=handler,
            heartbeat_interval=0.05,
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/sessions", json={})
            session_key = created.json()["session_key"]
            started = await client.post(f"/api/sessions/{session_key}/runs", json={"content": "问题"})
            run_id = started.json()["run_id"]
            missing = await client.post(f"/api/sessions/{session_key}/runs/missing-run/cancel")
            assert missing.status_code == 404
            cancelled = await client.post(f"/api/sessions/{session_key}/runs/{run_id}/cancel")
            assert cancelled.status_code == 202
            _, body = await _read_stream(client, started.json()["stream_url"])
            assert "stream closed" in body

    asyncio.run(scenario())


def test_startup_interrupts_a_running_session_without_resuming(tmp_path: Path) -> None:
    calls: list[str] = []

    async def handler(context: RunContext) -> None:
        calls.append(context.content)
        await context.emit({"type": "run.completed", "answer": "新回答"})

    database = tmp_path / "sessions.sqlite3"
    store = SessionStore(database)
    created = store.create("课题")
    session_key = created["session_key"]
    store.append_message(session_key, "user", "中断前的问题")
    store.save_result(session_key, "analysis", {"summary": "已保存"})
    store.mark_running(session_key, "2026-10-21T00:00:00+00:00")

    app = create_app(
        settings_path=_settings(tmp_path),
        database_path=database,
        run_handler=handler,
        heartbeat_interval=0.05,
    )
    assert calls == []
    loaded = app.state.sessions.get(session_key)
    assert loaded["status"] == "interrupted"
    assert loaded["run_started_at"] is None
    assert loaded["messages"][0]["content"] == "中断前的问题"
    assert loaded["results"]["analysis"] == {"summary": "已保存"}

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            started = await client.post(f"/api/sessions/{session_key}/runs", json={"content": "继续"})
            assert started.status_code == 202
            await _read_stream(client, started.json()["stream_url"])
            again = await client.get(f"/api/sessions/{session_key}")
            contents = [item["content"] for item in again.json()["messages"]]
            assert contents[0] == "中断前的问题"
            assert "继续" in contents

    asyncio.run(scenario())
    assert calls == ["继续"]
