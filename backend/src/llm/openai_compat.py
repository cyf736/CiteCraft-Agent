from __future__ import annotations

from typing import Any

import httpx

from src.repositories.settings.json import Settings, SettingsError


class ModelError(Exception):
    """模型调用失败。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ModelClient:
    """按档位调用 OpenAI 兼容的对话和 embedding 接口。"""

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http

    async def chat(self, profile_name: str, messages: list[dict[str, str]]) -> str:
        profile = self._settings.profile(profile_name)
        response = await self._http.post(
            _join(profile.api_base, "chat/completions"),
            headers=_headers(profile.api_key()),
            json={"model": profile.model, "messages": messages},
        )
        _raise_for_status(response)
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ModelError("对话响应缺少文本")
        return content

    async def embed(self, profile_name: str, text: str) -> list[float]:
        profile = self._settings.profile(profile_name)
        response = await self._http.post(
            _join(profile.api_base, "embeddings"),
            headers=_headers(profile.api_key()),
            json={"model": profile.model, "input": text},
        )
        _raise_for_status(response)
        vector = response.json()["data"][0]["embedding"]
        if not isinstance(vector, list) or not all(isinstance(item, int | float) for item in vector):
            raise ModelError("embedding 响应缺少数值向量")
        return [float(item) for item in vector]

    async def check_connectivity(self, profile_name: str) -> dict[str, Any]:
        try:
            if profile_name == "embedding":
                await self.embed(profile_name, "ping")
            else:
                await self.chat(profile_name, [{"role": "user", "content": "ping"}])
        except SettingsError:
            raise
        except ModelError as exc:
            return {"ok": False, "name": profile_name, "message": exc.message}
        except (httpx.HTTPError, KeyError) as exc:
            return {"ok": False, "name": profile_name, "message": str(exc)}
        return {"ok": True, "name": profile_name}


def _join(api_base: str, suffix: str) -> str:
    return api_base.rstrip("/") + "/" + suffix


def _headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code >= 400:
        raise ModelError(f"模型接口返回 {response.status_code}")
