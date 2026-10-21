from typing import Literal, cast
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MONGO_URL_BY_ENV = {
    "dev": "mongodb://localhost:27017/daily-trends-dev",
    "test": "mongodb://localhost:27017/daily-trends-test",
}
# Signs tokens outside production only: anyone can read it here.
_DEVELOPMENT_AUTH_SECRET_KEY = "dev-only-auth-secret-key-never-used-in-production"
_MIN_AUTH_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    # `MONGO_URL` can hold credentials and `AUTH_SECRET_KEY` is a secret, so errors never show
    # input values.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    env: Literal["production", "dev", "test"] = "dev"
    mongo_url: str = _MONGO_URL_BY_ENV["dev"]
    port: int = 5000
    timezone: ZoneInfo = ZoneInfo("Europe/Madrid")
    scrape_timeout_seconds: float = Field(default=10, gt=0)
    scrape_schedule_enabled: bool = True
    scrape_interval_seconds: float = Field(default=7200, gt=0)
    auth_secret_key: SecretStr = SecretStr(_DEVELOPMENT_AUTH_SECRET_KEY)
    auth_token_ttl_seconds: int = Field(default=28800, gt=0)

    @model_validator(mode="before")
    @classmethod
    def _defaults_for_env(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        values = cast(dict[str, object], data)
        env = values.get("env", "dev")
        if env == "production":
            required = ("mongo_url", "auth_secret_key")
            missing = [name.upper() for name in required if values.get(name) is None]
            if missing:
                verb = "is" if len(missing) == 1 else "are"
                raise ValueError(f"{' and '.join(missing)} {verb} required when ENV is production")
            return values
        if values.get("mongo_url") is not None:
            return values
        # An unknown ENV gets no default; the `env` field reports it.
        default = _MONGO_URL_BY_ENV.get(str(env))
        return values if default is None else {**values, "mongo_url": default}

    @field_validator("auth_secret_key")
    @classmethod
    def _long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < _MIN_AUTH_SECRET_KEY_LENGTH:
            raise ValueError(
                f"AUTH_SECRET_KEY must have at least {_MIN_AUTH_SECRET_KEY_LENGTH} characters"
            )
        return value
