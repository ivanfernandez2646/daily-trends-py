from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: Literal["production", "dev", "test"] = "dev"
    mongo_url: str = "mongodb://localhost:27017/daily-trends"
    port: int = 5000
