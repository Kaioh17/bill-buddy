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


# ---- Plaid and token encryption settings ----


def test_plaid_base_url_follows_env():
    assert make(plaid_env="sandbox").plaid_base_url == "https://sandbox.plaid.com"
    assert make(plaid_env="production").plaid_base_url == "https://production.plaid.com"


def test_unknown_plaid_env_rejected():
    with pytest.raises(ValidationError):
        make(plaid_env="development")


def test_plaid_api_version_is_pinned_by_default():
    assert make().plaid_api_version == "2020-09-14"


@pytest.mark.parametrize(
    "name", ["PLAID_CLIENT_ID", "PLAID_SECRET", "TOKEN_ENCRYPTION_KEY"]
)
def test_plaid_settings_are_required(monkeypatch, name):
    monkeypatch.delenv(name)
    with pytest.raises(ValidationError):
        make()


@pytest.mark.parametrize("bad", ["", "short", "change-me-" + "x" * 40, "!" * 44])
def test_encryption_key_must_be_a_valid_fernet_key(bad):
    with pytest.raises(ValidationError):
        make(token_encryption_key=bad)


def test_secrets_are_not_shown_in_repr():
    shown = repr(make())
    assert "test-plaid-secret" not in shown
    assert "hLDLg6EamhHY5C1yygf6am8X4MgRwy" not in shown
