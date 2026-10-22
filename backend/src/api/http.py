from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from src.repositories.settings.json import SettingsError


def error(message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"message": message, "status": status}})


async def read_body(request: Request) -> dict:
    # 允许不带正文的 POST。
    raw = await request.body()
    if raw == b"":
        return {}
    payload = await request.json()
    if not isinstance(payload, dict):
        raise SettingsError("请求正文必须是 JSON 对象")
    return payload
