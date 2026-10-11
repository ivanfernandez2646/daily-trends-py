from typing import Literal, cast

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MONGO_URL_BY_ENV = {
    "dev": "mongodb://localhost:27017/daily-trends-dev",
    "test": "mongodb://localhost:27017/daily-trends-test",
}


class Settings(BaseSettings):
    # `MONGO_URL` can hold credentials, so errors never show input values.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    env: Literal["production", "dev", "test"] = "dev"
    mongo_url: str = _MONGO_URL_BY_ENV["dev"]
    port: int = 5000
    scrap_timeout_seconds: float = Field(default=10, gt=0)
    scrap_cooldown_seconds: float = Field(default=300, ge=0)

    @model_validator(mode="before")
    @classmethod
    def _default_mongo_url_for_env(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        values = cast(dict[str, object], data)
        if values.get("mongo_url") is not None:
            return values
        env = values.get("env", "dev")
        if env == "production":
            raise ValueError("MONGO_URL is required when ENV is production")
        # An unknown ENV gets no default; the `env` field reports it.
        default = _MONGO_URL_BY_ENV.get(str(env))
        return values if default is None else {**values, "mongo_url": default}
