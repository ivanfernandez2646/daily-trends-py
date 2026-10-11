from pydantic_settings import SettingsConfigDict

from daily_trends_py.apps.cms_backend.settings import Settings


class IsolatedSettings(Settings):
    """Settings that never read `.env`, so a developer's file cannot point tests elsewhere."""

    model_config = SettingsConfigDict(env_file=None)
