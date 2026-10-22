from __future__ import annotations

import json
import shutil
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from src.api.app import create_app


EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "settings.example.json"
SECRET = "super-secret-value"


def _copy_settings(tmp_path: Path) -> Path:
    target = tmp_path / "settings.json"
    shutil.copyfile(EXAMPLE, target)
    return target


def test_settings_hide_secrets_and_reject_unknown_profiles(tmp_path: Path) -> None:
    path = _copy_settings(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["profiles"]["orchestrator"]["api_key"] = SECRET
    path.write_text(json.dumps(raw), encoding="utf-8")

    app = create_app(settings_path=path, database_path=tmp_path / "sessions.sqlite3")
    with TestClient(app) as client:
        current = client.get("/api/settings")
        assert current.status_code == 200
        body = current.json()
        assert set(body["profiles"]) == {"orchestrator", "analysis", "direction", "embedding"}
        assert SECRET not in current.text

        missing = client.put("/api/settings/profiles/not-a-profile", json={"api_base": "http://other"})
        assert missing.status_code == 404
        error = missing.json()["error"]
        assert error["status"] == 404
        assert error["message"]


def test_profile_address_survives_a_new_process(tmp_path: Path) -> None:
    path = _copy_settings(tmp_path)
    database = tmp_path / "sessions.sqlite3"
    address = "http://models.example/v1"

    first = create_app(settings_path=path, database_path=database)
    with TestClient(first) as client:
        updated = client.put("/api/settings/profiles/analysis", json={"api_base": address, "api_key": SECRET})
        assert updated.status_code == 200
        assert SECRET not in updated.text

    second = create_app(settings_path=path, database_path=database)
    with TestClient(second) as client:
        body = client.get("/api/settings")
    assert body.status_code == 200
    assert body.json()["profiles"]["analysis"]["api_base"] == address
    assert SECRET not in body.text
    assert SECRET not in path.read_text(encoding="utf-8")


def test_connectivity_reports_success_and_failure(tmp_path: Path) -> None:
    path = _copy_settings(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"embedding": [1.0]}]})
        return httpx.Response(503, json={"error": "down"})

    app = create_app(
        settings_path=path,
        database_path=tmp_path / "sessions.sqlite3",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with TestClient(app) as client:
        success = client.post("/api/settings/model-connectivity", json={"name": "embedding"})
        failure = client.post("/api/settings/model-connectivity", json={"name": "analysis"})

    assert success.status_code == 200
    assert success.json()["ok"] is True
    assert success.json()["name"] == "embedding"
    assert failure.status_code == 200
    assert failure.json()["ok"] is False
    assert failure.json()["name"] == "analysis"
