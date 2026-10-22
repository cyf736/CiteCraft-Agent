from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from src.llm.openai_compat import ModelClient
from src.repositories.settings.json import SettingsError, load_settings


EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "settings.example.json"


def test_chat_and_embedding_use_the_requested_profile() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"embedding": [0.25, 4]}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "检索方向"}}]})

    async def scenario() -> None:
        settings = load_settings(EXAMPLE)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = ModelClient(settings, http)
            text = await client.chat("orchestrator", [{"role": "user", "content": "问题"}])
            vector = await client.embed("embedding", "问题")
        assert text == "检索方向"
        assert vector == [0.25, 4.0]
        bodies = [json.loads(request.content) for request in seen]
        assert [body["model"] for body in bodies] == ["orchestrator", "embedding"]
        assert seen[0].url.path.endswith("/chat/completions")
        assert seen[1].url.path.endswith("/embeddings")

    asyncio.run(scenario())


def test_unknown_profile_fails_without_request() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "不应返回"}}]})

    async def scenario() -> None:
        settings = load_settings(EXAMPLE)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = ModelClient(settings, http)
            with pytest.raises(SettingsError, match="missing-profile"):
                await client.chat("missing-profile", [{"role": "user", "content": "问题"}])

    asyncio.run(scenario())
    assert seen == []
