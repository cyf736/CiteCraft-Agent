from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from src.api.http import read_body
from src.repositories.sessions.sqlite import SessionStore
from src.services.session_runs import AppError, RunManager, iter_sse


def create_sessions_router(sessions: SessionStore, runs: RunManager) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    @router.get("")
    async def list_sessions() -> dict:
        return {"sessions": sessions.list_sessions()}

    @router.post("", status_code=201)
    async def create_session(request: Request) -> dict:
        body = await read_body(request)
        # 创建会话时标题可以不传。
        title = body.get("title", "新会话")
        return sessions.create(title)

    @router.get("/{session_key}")
    async def get_session(session_key: str) -> dict:
        return sessions.get(session_key)

    @router.delete("/{session_key}")
    async def delete_session(session_key: str) -> dict:
        sessions.delete(session_key)
        return {"session_key": session_key, "deleted": True}

    @router.post("/{session_key}/runs", status_code=202)
    async def start_run(session_key: str, request: Request) -> dict:
        body = await read_body(request)
        if "content" not in body:
            raise AppError("缺少发言内容", 400)
        return await runs.start(session_key, body["content"])

    @router.post("/{session_key}/runs/{run_id}/cancel", status_code=202)
    async def cancel_run(session_key: str, run_id: str) -> dict:
        return runs.cancel(session_key, run_id)

    @router.get("/{session_key}/runs/{run_id}/stream")
    async def stream_run(session_key: str, run_id: str) -> StreamingResponse:
        runs.require(session_key, run_id)

        async def generate():
            async for chunk in iter_sse(runs.subscribe(session_key, run_id), runs.heartbeat_interval):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    return router
