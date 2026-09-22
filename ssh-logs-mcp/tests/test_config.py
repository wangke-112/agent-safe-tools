import json

import pytest

from ssh_logs_mcp.config import ConfigError, get_env, load_envs


def _write_config(path, envs):
    path.write_text(json.dumps({"envs": envs}), encoding="utf-8")


def test_load_and_get(monkeypatch, tmp_path):
    path = tmp_path / "servers.json"
    _write_config(path, {"test": {"host": "h", "user": "u", "password": "p"}})
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(path))

    assert "test" in load_envs()
    env = get_env("test")
    assert env.host == "h"
    assert env.port == 22


def test_alt_port_and_key(monkeypatch, tmp_path):
    path = tmp_path / "servers.json"
    _write_config(
        path,
        {"k": {"host": "h", "user": "u", "key_path": "/tmp/id", "altPort": 2222}},
    )
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(path))

    env = get_env("k")
    assert env.alt_port == 2222
    assert env.key_path == "/tmp/id"


def test_forbidden_env_is_rejected(monkeypatch, tmp_path):
    path = tmp_path / "servers.json"
    _write_config(
        path, {"prd": {"host": "h", "user": "u", "password": "p", "forbidden": True}}
    )
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(path))

    with pytest.raises(ConfigError):
        get_env("prd")


def test_missing_config(monkeypatch, tmp_path):
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(tmp_path / "nope.json"))
    with pytest.raises(ConfigError):
        load_envs()
