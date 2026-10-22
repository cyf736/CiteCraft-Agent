from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.api.app import create_app


BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
EXAMPLE = BACKEND / "config" / "settings.example.json"
COMPOSE = REPO / "docker-compose.yml"
README = REPO / "README.md"


def test_example_config_has_profiles_and_milvus_without_minio_or_secrets() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    text = EXAMPLE.read_text(encoding="utf-8").lower()
    assert set(raw["profiles"]) == {"luna_agent", "default_agent", "solar_agent", "embedding"}
    assert raw["milvus"]["host"] == "127.0.0.1"
    assert raw["milvus"]["port"] == 19530
    assert "minio" not in text
    for profile in raw["profiles"].values():
        assert set(profile) == {"api_base", "model", "api_key_env"}
        assert "api_key" not in profile


def test_compose_gives_minio_address_only_to_milvus() -> None:
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = document["services"]
    assert set(services) == {"etcd", "minio", "milvus"}
    assert set(services["milvus"]["depends_on"]) == {"etcd", "minio"}
    assert services["milvus"]["environment"]["MINIO_ADDRESS"] == "minio:9000"
    for name in ("etcd", "minio"):
        rendered = yaml.safe_dump(services[name])
        assert "MINIO_ADDRESS" not in rendered


def test_readme_uses_the_example_config_keys() -> None:
    text = README.read_text(encoding="utf-8")
    for key in (
        "luna_agent",
        "default_agent",
        "solar_agent",
        "embedding",
        "api_base",
        "model",
        "api_key_env",
        "milvus.host",
        "milvus.port",
        "settings.example.json",
    ):
        assert key in text


def test_health_with_example_config(tmp_path: Path) -> None:
    app = create_app(settings_path=EXAMPLE, database_path=tmp_path / "sessions.sqlite3")
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
