from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROFILE_NAMES = ("orchestrator", "analysis", "direction", "embedding")
SECRET_FIELDS = {"api_key", "secret", "token", "password"}


class SettingsError(Exception):
    """配置不存在或档位名称无效。"""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class Profile:
    name: str
    api_base: str
    model: str
    api_key_env: str

    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")

    def public(self) -> dict[str, str]:
        return {
            "api_base": self.api_base,
            "model": self.model,
            "api_key_env": self.api_key_env,
        }


@dataclass(frozen=True)
class Settings:
    path: Path
    milvus_host: str
    milvus_port: int
    profiles: dict[str, Profile]

    def profile(self, name: str) -> Profile:
        try:
            return self.profiles[name]
        except KeyError as exc:
            raise SettingsError(f"档位不存在：{name}", status=404) from exc

    def public(self) -> dict[str, Any]:
        return {
            "milvus": {"host": self.milvus_host, "port": self.milvus_port},
            "profiles": {name: profile.public() for name, profile in self.profiles.items()},
        }


def load_settings(path: Path) -> Settings:
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        milvus = raw["milvus"]
        profiles = {
            name: Profile(
                name=name,
                api_base=raw["profiles"][name]["api_base"],
                model=raw["profiles"][name]["model"],
                api_key_env=raw["profiles"][name]["api_key_env"],
            )
            for name in PROFILE_NAMES
        }
        host = milvus["host"]
        port = milvus["port"]
    except (KeyError, TypeError) as exc:
        raise SettingsError(f"配置不完整：{exc}") from exc
    return Settings(path=path, milvus_host=host, milvus_port=int(port), profiles=profiles)


def update_profile(path: Path, name: str, changes: dict[str, Any]) -> Settings:
    if name not in PROFILE_NAMES:
        raise SettingsError(f"档位不存在：{name}", status=404)
    raw = json.loads(path.read_text(encoding="utf-8"))
    current = dict(raw["profiles"][name])
    for key, value in changes.items():
        if key in SECRET_FIELDS:
            continue
        current[key] = value
    raw["profiles"][name] = current
    _write_json(path, raw)
    return load_settings(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
