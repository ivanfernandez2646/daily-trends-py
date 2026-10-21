from pydantic_settings import SettingsConfigDict

from daily_trends_py.apps.cms_backend.settings import Settings


class IsolatedSettings(Settings):
    """Settings that never read `.env`, so a developer's file cannot point tests elsewhere.

    Scheduled scraping is off, so no test scrapes in the background unless it asks to.
    """

    model_config = SettingsConfigDict(env_file=None)

    scrape_schedule_enabled: bool = False
