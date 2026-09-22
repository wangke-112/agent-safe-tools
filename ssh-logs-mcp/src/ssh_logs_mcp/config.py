"""Environment configuration loading.

Credentials live in a user-owned file (default ``~/.config/ssh-logs-mcp/servers.json``),
never in this package or any repository.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "ssh-logs-mcp" / "servers.json"


class ConfigError(ValueError):
    """Raised for missing or invalid configuration."""


@dataclass(frozen=True)
class ServerEnv:
    name: str
    host: str
    port: int = 22
    alt_port: int | None = None
    user: str = ""
    password: str = ""
    key_path: str | None = None
    forbidden: bool = False
    description: str = ""


def config_path() -> Path:
    return Path(os.getenv("SSH_LOGS_CONFIG", str(DEFAULT_CONFIG_PATH))).expanduser()


def _from_mapping(name: str, data: dict) -> ServerEnv:
    return ServerEnv(
        name=name,
        host=str(data.get("host", "")),
        port=int(data.get("port", 22)),
        alt_port=int(data["altPort"]) if data.get("altPort") else None,
        user=str(data.get("user", "")),
        password=str(data.get("password", "")),
        key_path=data.get("key_path") or data.get("keyPath"),
        forbidden=bool(data.get("forbidden", False)),
        description=str(data.get("desc", data.get("description", ""))),
    )


def load_envs() -> dict[str, ServerEnv]:
    path = config_path()
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("envs", data)
    return {name: _from_mapping(name, entry) for name, entry in entries.items()}


def get_env(name: str) -> ServerEnv:
    envs = load_envs()
    if name not in envs:
        raise ConfigError(f"unknown env '{name}'. Available: {', '.join(envs)}")
    env = envs[name]
    if env.forbidden:
        raise ConfigError(f"env '{name}' is disabled (forbidden=true)")
    if not env.host:
        raise ConfigError(f"env '{name}' is missing host")
    if not env.password and not env.key_path:
        raise ConfigError(f"env '{name}' needs password or key_path")
    return env
