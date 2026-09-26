import json

import pytest

from ssh_logs_mcp.config import ConfigError, get_env, load_envs


def _write_config(path, envs):
    path.write_text(json.dumps({"envs": envs}), encoding="utf-8")


def test_load_and_get(monkeypatch, tmp_path):
    path = tmp_path / "servers.json"
    _write_config(path, {"test": {"host": "h", "user": "u", "password_env": "TEST_PW", "log_root": "/var/log", "known_hosts": "/tmp/known_hosts"}})
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(path))
    monkeypatch.setenv("TEST_PW", "p")

    assert "test" in load_envs()
    env = get_env("test")
    assert env.host == "h"
    assert env.port == 22


def test_alt_port_and_key(monkeypatch, tmp_path):
    path = tmp_path / "servers.json"
    _write_config(
        path,
        {"k": {"host": "h", "user": "u", "key_path": "/tmp/id", "altPort": 2222, "log_root": "/var/log", "known_hosts": "/tmp/known_hosts"}},
    )
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(path))

    env = get_env("k")
    assert env.alt_port == 2222
    assert env.key_path == "/tmp/id"


def test_forbidden_env_is_rejected(monkeypatch, tmp_path):
    path = tmp_path / "servers.json"
    _write_config(
        path, {"prd": {"host": "h", "user": "u", "password_env": "TEST_PW", "log_root": "/var/log", "known_hosts": "/tmp/known_hosts", "forbidden": True}}
    )
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(path))

    with pytest.raises(ConfigError):
        get_env("prd")


def test_missing_config(monkeypatch, tmp_path):
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(tmp_path / "nope.json"))
    with pytest.raises(ConfigError):
        load_envs()


def test_inline_password_is_rejected(monkeypatch, tmp_path):
    path = tmp_path / "servers.json"
    _write_config(path, {"test": {"host": "h", "user": "u", "password": "secret", "log_root": "/var/log", "known_hosts": "/tmp/known_hosts"}})
    monkeypatch.setenv("SSH_LOGS_CONFIG", str(path))
    with pytest.raises(ConfigError, match="inline passwords"):
        get_env("test")
