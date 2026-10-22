from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.http import error
from src.api.routers.sessions import create_sessions_router
from src.api.routers.settings import create_settings_router
from src.llm.openai_compat import ModelClient
from src.repositories.sessions.sqlite import SessionStore
from src.repositories.settings.json import SettingsError, load_settings
from src.services.session_runs import AppError, RunContext, RunManager


def create_app(
    settings_path: Path | None = None,
    database_path: Path | None = None,
    run_handler: Callable[[RunContext], Awaitable[None]] | None = None,
    heartbeat_interval: float = 15.0,
    http_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    root = Path(__file__).resolve().parents[2]
    if settings_path is None:
        settings_path = _default_settings_path(root)
    if database_path is None:
        database_path = root / "data" / "sessions.sqlite3"
    settings = load_settings(settings_path)
    sessions = SessionStore(database_path)
    sessions.recover_interrupted()
    if http_client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True
    else:
        client = http_client
        owns_client = False
    models = ModelClient(settings, client)
    runs = RunManager(sessions, run_handler, heartbeat_interval)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            if owns_client:
                await client.aclose()

    app = FastAPI(title="CiteCraft", lifespan=lifespan)
    app.state.settings_path = settings_path
    app.state.sessions = sessions
    app.state.models = models
    app.state.runs = runs
    app.include_router(create_settings_router(settings_path, client))
    app.include_router(create_sessions_router(sessions, runs))

    @app.exception_handler(SettingsError)
    async def settings_error(_: Request, exc: SettingsError) -> JSONResponse:
        return error(exc.message, exc.status)

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        return error(exc.message, exc.status)

    @app.exception_handler(KeyError)
    async def missing(_: Request, exc: KeyError) -> JSONResponse:
        return error(f"不存在：{exc.args[0]}", 404)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def main() -> None:
    uvicorn.run("src.api.app:create_app", factory=True, host="127.0.0.1", port=8000)


def _default_settings_path(root: Path) -> Path:
    local = root / "config" / "settings.json"
    if local.exists():
        return local
    return root / "config" / "settings.example.json"
