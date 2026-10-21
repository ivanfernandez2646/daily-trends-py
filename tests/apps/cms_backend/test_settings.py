from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from daily_trends_py.apps.cms_backend.settings import Settings

_VARIABLES = (
    "ENV",
    "MONGO_URL",
    "PORT",
    "TIMEZONE",
    "SCRAPE_TIMEOUT_SECONDS",
    "SCRAPE_SCHEDULE_ENABLED",
    "SCRAPE_INTERVAL_SECONDS",
    "SCRAPE_COOLDOWN_SECONDS",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in _VARIABLES:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    # `.env` is read from the working directory.
    monkeypatch.chdir(tmp_path)


def write_env_file(content: str) -> None:
    Path(".env").write_text(content)


def test_uses_dev_defaults_when_environment_and_env_file_are_empty() -> None:
    settings = Settings()

    assert settings.env == "dev"
    assert settings.mongo_url == "mongodb://localhost:27017/daily-trends-dev"
    assert settings.port == 5000
    assert settings.timezone == ZoneInfo("Europe/Madrid")
    assert settings.scrape_timeout_seconds == 10
    assert settings.scrape_schedule_enabled is True
    assert settings.scrape_interval_seconds == 7200


def test_uses_the_test_database_by_default_when_env_is_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENV", "test")

    settings = Settings()

    assert settings.mongo_url == "mongodb://localhost:27017/daily-trends-test"


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("MONGO_URL", "mongodb://mongo:27017/other")
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("TIMEZONE", "America/New_York")
    monkeypatch.setenv("SCRAPE_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("SCRAPE_SCHEDULE_ENABLED", "false")
    monkeypatch.setenv("SCRAPE_INTERVAL_SECONDS", "60")

    settings = Settings()

    assert settings.env == "production"
    assert settings.mongo_url == "mongodb://mongo:27017/other"
    assert settings.port == 8080
    assert settings.timezone == ZoneInfo("America/New_York")
    assert settings.scrape_timeout_seconds == 2.5
    assert settings.scrape_schedule_enabled is False
    assert settings.scrape_interval_seconds == 60


def test_reads_lower_case_variable_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("port", "8080")

    settings = Settings()

    assert settings.port == 8080


def test_reads_values_from_the_env_file() -> None:
    write_env_file("PORT=5123\n")

    settings = Settings()

    assert settings.port == 5123


def test_environment_wins_over_the_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    write_env_file("PORT=5123\n")
    monkeypatch.setenv("PORT", "8080")

    settings = Settings()

    assert settings.port == 8080


def test_env_from_the_env_file_selects_the_default_database() -> None:
    write_env_file("ENV=test\n")

    settings = Settings()

    assert settings.mongo_url == "mongodb://localhost:27017/daily-trends-test"


def test_an_explicit_mongo_url_wins_over_the_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("MONGO_URL", "mongodb://mongo:27017/other")

    settings = Settings()

    assert settings.mongo_url == "mongodb://mongo:27017/other"


def test_ignores_unrelated_variables_in_the_env_file() -> None:
    write_env_file("UNRELATED=value\nPORT=5123\n")

    settings = Settings()

    assert settings.port == 5123


def test_requires_mongo_url_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")

    with pytest.raises(ValidationError, match="MONGO_URL"):
        Settings()


def test_errors_never_show_the_mongo_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("MONGO_URL", "mongodb://user:secret@mongo:27017/daily-trends")
    monkeypatch.setenv("PORT", "abc")

    with pytest.raises(ValidationError) as error:
        Settings()

    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ENV", "staging"),
        ("PORT", "abc"),
        ("TIMEZONE", "Mars/Olympus"),
        ("SCRAPE_TIMEOUT_SECONDS", "0"),
        ("SCRAPE_SCHEDULE_ENABLED", "sometimes"),
        ("SCRAPE_INTERVAL_SECONDS", "0"),
        ("SCRAPE_INTERVAL_SECONDS", "-1"),
    ],
)
def test_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings()


def test_ignores_a_leftover_cooldown_in_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRAPE_COOLDOWN_SECONDS", "-1")

    settings = Settings()

    assert not hasattr(settings, "scrape_cooldown_seconds")


def test_ignores_a_leftover_cooldown_in_the_env_file() -> None:
    write_env_file("SCRAPE_COOLDOWN_SECONDS=-1\n")

    settings = Settings()

    assert not hasattr(settings, "scrape_cooldown_seconds")


def test_names_the_timezone_variable_when_it_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMEZONE", "Mars/Olympus")

    with pytest.raises(ValidationError, match="timezone"):
        Settings()
