"""SSH transport: connect, execute one command, decode the output."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Any

import paramiko

from .config import ServerEnv

CONNECT_TIMEOUT = 12
EXEC_TIMEOUT = 60


def smart_decode(data: bytes) -> str:
    """Try UTF-8 first, then GBK (common for CJK logs), then fall back."""

    for encoding in ("utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def run_command(
    env: ServerEnv,
    command: str,
    *,
    connect_timeout: int = CONNECT_TIMEOUT,
    exec_timeout: int = EXEC_TIMEOUT,
) -> dict[str, Any]:
    client = paramiko.SSHClient()
    known_hosts = Path(env.known_hosts).expanduser() if env.known_hosts else Path.home() / ".ssh" / "known_hosts"
    if not known_hosts.exists() and not env.host_key_fingerprint:
        raise ConnectionError(f"known_hosts file not found: {known_hosts}")
    if known_hosts.exists():
        client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(_FingerprintPolicy(env.host_key_fingerprint))

    ports = [env.port] + ([env.alt_port] if env.alt_port else [])
    kwargs: dict[str, Any] = {
        "username": env.user,
        "timeout": connect_timeout,
        "banner_timeout": connect_timeout,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if env.key_path:
        kwargs["key_filename"] = env.key_path
    else:
        kwargs["password"] = os.environ[env.password_env]

    last_error: Exception | None = None
    used_port = env.port
    for port in ports:
        try:
            client.connect(hostname=env.host, port=port, **kwargs)
            used_port = port
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001 - surface whichever port failed last
            last_error = exc
    if last_error is not None:
        raise ConnectionError(f"connect failed {env.host}:{ports}: {last_error}")

    try:
        _stdin, stdout, stderr = client.exec_command(command, timeout=exec_timeout)
        out = smart_decode(stdout.read())
        err = smart_decode(stderr.read())
        exit_code = stdout.channel.recv_exit_status()
    finally:
        client.close()

    return {
        "env": env.name,
        "host": env.host,
        "port": used_port,
        "command": command,
        "exit_code": exit_code,
        "stdout": out,
        "stderr": err,
    }


class _FingerprintPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(self, expected: str | None):
        self.expected = expected

    def missing_host_key(self, client, hostname, key):
        if not self.expected:
            raise paramiko.SSHException(f"unknown host key for {hostname}; add it to known_hosts")
        digest = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode("ascii").rstrip("=")
        actual = f"SHA256:{digest}"
        if actual != self.expected:
            raise paramiko.SSHException(f"host key fingerprint mismatch for {hostname}")
