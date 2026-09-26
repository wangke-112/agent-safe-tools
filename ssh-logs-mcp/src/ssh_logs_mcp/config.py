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
    password_env: str | None = None
    key_path: str | None = None
    log_root: str = ""
    known_hosts: str | None = None
    host_key_fingerprint: str | None = None
    allow_raw_commands: bool = False
    forbidden: bool = False
    description: str = ""


def config_path() -> Path:
    return Path(os.getenv("SSH_LOGS_CONFIG", str(DEFAULT_CONFIG_PATH))).expanduser()


def _from_mapping(name: str, data: dict) -> ServerEnv:
    if data.get("password"):
        raise ConfigError(f"env '{name}' must use key_path or password_env; inline passwords are blocked")
    return ServerEnv(
        name=name,
        host=str(data.get("host", "")),
        port=int(data.get("port", 22)),
        alt_port=int(data["altPort"]) if data.get("altPort") else None,
        user=str(data.get("user", "")),
        password="",
        password_env=data.get("password_env") or data.get("passwordEnv"),
        key_path=data.get("key_path") or data.get("keyPath"),
        log_root=str(data.get("log_root", data.get("logRoot", ""))),
        known_hosts=data.get("known_hosts") or data.get("knownHosts"),
        host_key_fingerprint=data.get("host_key_fingerprint") or data.get("hostKeyFingerprint"),
        allow_raw_commands=bool(data.get("allow_raw_commands", False)),
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
    if not env.log_root:
        raise ConfigError(f"env '{name}' is missing log_root")
    if env.password:
        raise ConfigError(f"env '{name}' must use key_path or password_env; inline passwords are blocked")
    if not env.password_env and not env.key_path:
        raise ConfigError(f"env '{name}' needs key_path or password_env")
    if env.password_env and not os.getenv(env.password_env):
        raise ConfigError(f"environment variable {env.password_env} is not set")
    if not env.known_hosts and not env.host_key_fingerprint:
        raise ConfigError(f"env '{name}' needs known_hosts or host_key_fingerprint")
    return env
