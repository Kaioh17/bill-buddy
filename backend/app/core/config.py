"""Settings loaded from environment variables (and .env). See .env.example."""

from functools import lru_cache
from typing import Annotated, Literal

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["dev", "prod"] = "dev"
    log_level: str | None = None  # defaults to DEBUG in dev, INFO in prod

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/billbuddy"
    )

    # NoDecode lets us accept a plain comma separated string instead of JSON.
    cors_origins: Annotated[list[str], NoDecode] = []

    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    # Also the inactivity timeout: the token is re-issued on each authenticated request.
    access_token_expire_minutes: int = Field(15, gt=0)
    # Hard cap on a session however active the user is.
    session_max_hours: int = Field(12, gt=0)

    plaid_client_id: str = Field(min_length=1)
    plaid_secret: SecretStr
    plaid_env: Literal["sandbox", "production"] = "sandbox"
    # Pinned so a Plaid API change can never alter responses under us.
    plaid_api_version: str = "2020-09-14"
    # Public https URL Plaid calls with updates. Empty disables webhooks.
    plaid_webhook_url: str | None = None

    # Encrypts Plaid access tokens at rest. Losing it means every account must relink.
    token_encryption_key: SecretStr

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard(cls, v: list[str]):
        # Credentials are allowed, and browsers refuse "*" with credentials anyway.
        if "*" in v:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'")
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def _strong_secret(cls, v: SecretStr):
        s = v.get_secret_value()
        if len(s) < 32 or s.startswith("change-me"):
            raise ValueError(
                "JWT_SECRET_KEY must be a random value of at least 32 characters"
            )
        return v

    @field_validator("token_encryption_key")
    @classmethod
    def _valid_fernet_key(cls, v: SecretStr):
        try:
            Fernet(v.get_secret_value())
        except ValueError:
            raise ValueError(
                "TOKEN_ENCRYPTION_KEY must be a Fernet key, see .env.example"
            ) from None
        return v

    @property
    def plaid_base_url(self) -> str:
        return f"https://{self.plaid_env}.plaid.com"

    @property
    def effective_log_level(self) -> str:
        return (
            self.log_level or ("DEBUG" if self.app_env == "dev" else "INFO")
        ).upper()


@lru_cache
def get_settings() -> Settings:
    return Settings()
