import json

import pytest

from safe_mysql_mcp.config import list_profile_names, load_profile


def test_env_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("SAFE_MYSQL_PROFILES", str(tmp_path / "missing.json"))
    monkeypatch.delenv("SAFE_MYSQL_PROFILE", raising=False)
    monkeypatch.setenv("MYSQL_HOST", "db.local")
    monkeypatch.setenv("MYSQL_USER", "readonly")
    monkeypatch.setenv("MYSQL_READ_ONLY", "true")

    profile = load_profile("default")
    assert profile.host == "db.local"
    assert profile.user == "readonly"
    assert profile.read_only is True


def test_profiles_file(monkeypatch, tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "profiles": {
                    "prod": {
                        "host": "10.0.0.9",
                        "user": "ro",
                        "password_env": "MYSQL_PROD_PASSWORD",
                        "read_only": True,
                        "allowed_schemas": ["app_prod"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SAFE_MYSQL_PROFILES", str(path))
    monkeypatch.setenv("MYSQL_PROD_PASSWORD", "secret")

    profile = load_profile("prod")
    assert profile.host == "10.0.0.9"
    assert profile.read_only is True
    assert profile.allowed_schemas == ("app_prod",)
    assert list_profile_names() == ["prod"]


def test_inline_password_is_rejected(monkeypatch, tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"profiles": {"prod": {"host": "db", "password": "secret"}}}), encoding="utf-8")
    monkeypatch.setenv("SAFE_MYSQL_PROFILES", str(path))
    with pytest.raises(ValueError, match="inline passwords"):
        load_profile("prod")
