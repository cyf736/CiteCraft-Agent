from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from src.repositories.sessions.sqlite import SessionStore, utc_now


class AppError(Exception):
    """路由层直接返回的错误。"""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class RunContext:
    session_key: str
    run_id: str
    content: str
    store: SessionStore
    cancellation: asyncio.Event
    _publish: Callable[[dict], None]

    async def emit(self, event: dict) -> None:
        event_type = event["type"]
        self.store.append_event(self.session_key, self.run_id, event_type, event)
        if event_type == "run.completed" and isinstance(event.get("answer"), str):
            self.store.append_message(self.session_key, "assistant", event["answer"])
        self._publish(event)


@dataclass
class _Run:
    session_key: str
    run_id: str
    events: list[dict] = field(default_factory=list)
    subscribers: list[asyncio.Queue[dict | None]] = field(default_factory=list)
    closed: bool = False
    task: asyncio.Task[None] | None = None
    cancellation: asyncio.Event = field(default_factory=asyncio.Event)


class RunManager:
    """接受发言并按 Paper-Agent 的方式把事件放进内存队列。"""

    def __init__(
        self,
        store: SessionStore,
        handler: Callable[[RunContext], Awaitable[None]] | None,
        heartbeat_interval: float,
    ) -> None:
        self.store = store
        self.handler = handler
        self.heartbeat_interval = heartbeat_interval
        self._runs: dict[str, _Run] = {}
        self._lock = threading.RLock()

    async def start(self, session_key: str, content: str) -> dict[str, str]:
        with self._lock:
            record = self.store.get(session_key)
            if record["status"] == "running" or record["run_started_at"]:
                raise AppError("session is already running", 409)
            run_id = uuid.uuid4().hex
            started_at = utc_now()
            self.store.mark_running(session_key, started_at)
            self.store.append_message(session_key, "user", content)
            state = _Run(session_key=session_key, run_id=run_id)
            self._runs[run_id] = state
        state.task = asyncio.create_task(self._execute(state, content))
        await asyncio.sleep(0)
        return {
            "session_key": session_key,
            "run_id": run_id,
            "status": "accepted",
            "stream_url": f"/api/sessions/{session_key}/runs/{run_id}/stream",
        }

    def _lookup(self, session_key: str, run_id: str) -> _Run:
        state = self._runs.get(run_id)
        if state is None or state.session_key != session_key:
            raise AppError("run not found", 404)
        return state

    def cancel(self, session_key: str, run_id: str) -> dict[str, str]:
        with self._lock:
            state = self._lookup(session_key, run_id)
            if state.closed or (state.task is not None and state.task.done()):
                return {"session_key": session_key, "run_id": run_id, "status": "already_finished"}
            already_requested = state.cancellation.is_set()
            state.cancellation.set()
            task = state.task
        if not already_requested:
            self._record(state, {"type": "cancel.requested", "message": "已收到停止请求"})
        if task is not None and not task.done():
            task.cancel()
        return {"session_key": session_key, "run_id": run_id, "status": "cancel_requested"}

    def require(self, session_key: str, run_id: str) -> None:
        self.store.get(session_key)
        with self._lock:
            self._lookup(session_key, run_id)

    async def subscribe(self, session_key: str, run_id: str):
        queue: asyncio.Queue[dict | None] = asyncio.Queue()
        with self._lock:
            state = self._lookup(session_key, run_id)
            history = list(state.events)
            closed = state.closed
            if not closed:
                state.subscribers.append(queue)
        try:
            for event in history:
                yield event
            if closed:
                return
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            with self._lock:
                if queue in state.subscribers:
                    state.subscribers.remove(queue)

    async def _execute(self, state: _Run, content: str) -> None:
        context = RunContext(
            state.session_key,
            state.run_id,
            content,
            self.store,
            state.cancellation,
            lambda event: self._publish(state, event),
        )
        status = "idle"
        try:
            if self.handler is None:
                await context.emit({"type": "run.failed", "message": "研究流程尚未注册"})
                status = "failed"
            else:
                await self.handler(context)
                if state.cancellation.is_set():
                    status = "cancelled"
                    self._record(state, {"type": "run.cancelled", "message": "运行已停止"})
                    return
        except asyncio.CancelledError:
            status = "cancelled"
            self._record(state, {"type": "run.cancelled", "message": "运行已停止"})
        except Exception as exc:
            status = "failed"
            self._record(state, {"type": "run.failed", "message": str(exc)})
        finally:
            self.store.finish(state.session_key, status)
            self._close(state)

    def _record(self, state: _Run, event: dict) -> None:
        event_type = event["type"]
        self.store.append_event(state.session_key, state.run_id, event_type, event)
        if event_type == "run.completed" and isinstance(event.get("answer"), str):
            self.store.append_message(state.session_key, "assistant", event["answer"])
        self._publish(state, event)

    def _publish(self, state: _Run, event: dict) -> None:
        with self._lock:
            state.events.append(event)
            subscribers = list(state.subscribers)
        for subscriber in subscribers:
            subscriber.put_nowait(event)

    def _close(self, state: _Run) -> None:
        with self._lock:
            if state.closed:
                return
            state.closed = True
            subscribers = list(state.subscribers)
        for subscriber in subscribers:
            subscriber.put_nowait(None)


def encode_sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def iter_sse(source, heartbeat_interval: float):
    """先补发已有事件，等待下一条时发送注释心跳。"""

    iterator = source.__aiter__()
    pending = asyncio.create_task(anext(iterator))
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=heartbeat_interval)
            if not done:
                yield ": heartbeat\n\n"
                continue
            try:
                event = pending.result()
            except StopAsyncIteration:
                break
            pending = asyncio.create_task(anext(iterator))
            yield encode_sse(event)
    finally:
        if not pending.done():
            pending.cancel()
    yield ": stream closed\n\n"
