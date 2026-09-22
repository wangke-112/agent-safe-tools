"""Profile loading.

Two sources, in priority order:

1. A profiles JSON file (multi-database): ``~/.config/safe-mysql-mcp/profiles.json``
   or the path in ``SAFE_MYSQL_PROFILES``.
2. Environment variables ( ``MYSQL_*`` ) for a single connection.

No credentials are ever hard-coded or written by this package.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_PROFILES_PATH = Path.home() / ".config" / "safe-mysql-mcp" / "profiles.json"


@dataclass(frozen=True)
class Profile:
    name: str
    host: str
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str | None = None
    charset: str = "utf8mb4"
    read_only: bool = True
    default_limit: int = 100
    max_limit: int = 1000
    connect_timeout: int = 8
    read_timeout: int = 120
    write_timeout: int = 120
    allowed_schemas: tuple[str, ...] = field(default_factory=tuple)


def profiles_path() -> Path:
    return Path(os.getenv("SAFE_MYSQL_PROFILES", str(DEFAULT_PROFILES_PATH))).expanduser()


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _from_mapping(name: str, data: dict[str, Any]) -> Profile:
    return Profile(
        name=name,
        host=str(data.get("host", "127.0.0.1")),
        port=int(data.get("port", 3306)),
        user=str(data.get("user", "root")),
        password=str(data.get("password", "")),
        database=data.get("database") or None,
        charset=str(data.get("charset", "utf8mb4")),
        read_only=bool(data.get("read_only", True)),
        default_limit=int(data.get("default_limit", 100)),
        max_limit=int(data.get("max_limit", 1000)),
        connect_timeout=int(data.get("connect_timeout", 8)),
        read_timeout=int(data.get("read_timeout", 120)),
        write_timeout=int(data.get("write_timeout", 120)),
        allowed_schemas=tuple(data.get("allowed_schemas", ()) or ()),
    )


def _from_env(name: str) -> Profile:
    return Profile(
        name=name,
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=_env_int(os.getenv("MYSQL_PORT"), 3306),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE") or None,
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        read_only=_env_bool(os.getenv("MYSQL_READ_ONLY"), True),
        default_limit=_env_int(os.getenv("MYSQL_DEFAULT_LIMIT"), 100),
        max_limit=_env_int(os.getenv("MYSQL_MAX_LIMIT"), 1000),
    )


def load_profiles() -> dict[str, Profile]:
    path = profiles_path()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("profiles", data)
        return {name: _from_mapping(name, entry) for name, entry in entries.items()}
    return {"default": _from_env("default")}


def active_profile_name() -> str:
    return os.getenv("SAFE_MYSQL_PROFILE", "default")


def list_profile_names() -> list[str]:
    return sorted(load_profiles().keys())


def load_profile(name: str | None = None) -> Profile:
    profiles = load_profiles()
    key = name or active_profile_name()
    if key not in profiles:
        raise KeyError(f"Unknown profile '{key}'. Available: {', '.join(profiles)}")
    return profiles[key]
