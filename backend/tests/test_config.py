import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET = "s" * 40


def make(**kw):
    return Settings(_env_file=None, jwt_secret_key=SECRET, **kw)


def test_cors_origins_split_on_commas():
    s = make(cors_origins="http://a.test, http://b.test ,")
    assert s.cors_origins == ["http://a.test", "http://b.test"]


def test_cors_defaults_to_none_allowed(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS")
    assert make().cors_origins == []


def test_wildcard_origin_rejected():
    with pytest.raises(ValidationError):
        make(cors_origins="*")


def test_short_or_placeholder_secret_rejected():
    for bad in ("short", "change-me-" + "x" * 40):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, jwt_secret_key=bad)


def test_log_level_defaults_by_env():
    assert make(app_env="dev").effective_log_level == "DEBUG"
    assert make(app_env="prod").effective_log_level == "INFO"
    assert make(app_env="prod", log_level="warning").effective_log_level == "WARNING"


def test_unknown_env_rejected():
    with pytest.raises(ValidationError):
        make(app_env="staging")
