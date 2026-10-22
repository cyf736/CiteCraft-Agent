from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, Request

from src.api.http import read_body
from src.llm.openai_compat import ModelClient
from src.repositories.settings.json import SettingsError, load_settings, update_profile


def create_settings_router(settings_path: Path, client: httpx.AsyncClient) -> APIRouter:
    router = APIRouter(prefix="/api/settings", tags=["settings"])

    @router.get("")
    async def get_settings() -> dict:
        return load_settings(settings_path).public()

    @router.put("/profiles/{name}")
    async def put_profile(name: str, request: Request) -> dict:
        body = await read_body(request)
        updated = update_profile(settings_path, name, body)
        request.app.state.models = ModelClient(updated, client)
        return updated.public()

    @router.post("/model-connectivity")
    async def connectivity(request: Request) -> dict:
        body = await read_body(request)
        if "name" not in body:
            raise SettingsError("缺少模型名称")
        return await request.app.state.models.check_connectivity(body["name"])

    return router
