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
    "AUTH_SECRET_KEY",
    "AUTH_TOKEN_TTL_SECONDS",
)

SECRET_KEY = "a-production-secret-key-of-48-characters-exactly"


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
    monkeypatch.setenv("AUTH_SECRET_KEY", SECRET_KEY)
    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", "3600")

    settings = Settings()

    assert settings.env == "production"
    assert settings.mongo_url == "mongodb://mongo:27017/other"
    assert settings.port == 8080
    assert settings.timezone == ZoneInfo("America/New_York")
    assert settings.scrape_timeout_seconds == 2.5
    assert settings.scrape_schedule_enabled is False
    assert settings.scrape_interval_seconds == 60
    assert settings.auth_secret_key.get_secret_value() == SECRET_KEY
    assert settings.auth_token_ttl_seconds == 3600


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


@pytest.mark.parametrize("env", ["dev", "test"])
def test_uses_a_fixed_development_secret_key_and_an_eight_hour_token_outside_production(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("ENV", env)

    settings = Settings()

    assert len(settings.auth_secret_key.get_secret_value()) >= 32
    assert settings.auth_secret_key == Settings().auth_secret_key
    assert settings.auth_token_ttl_seconds == 28800


def test_requires_the_secret_key_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("MONGO_URL", "mongodb://mongo:27017/daily-trends")

    with pytest.raises(ValidationError, match="AUTH_SECRET_KEY is required when ENV is production"):
        Settings()


def test_names_every_variable_production_requires(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")

    with pytest.raises(ValidationError, match="MONGO_URL and AUTH_SECRET_KEY are required"):
        Settings()


@pytest.mark.parametrize("env", ["production", "dev"])
def test_rejects_a_secret_key_shorter_than_32_characters_without_showing_it(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("ENV", env)
    monkeypatch.setenv("MONGO_URL", "mongodb://mongo:27017/daily-trends")
    monkeypatch.setenv("AUTH_SECRET_KEY", "twenty-char-secret!!")

    with pytest.raises(ValidationError) as error:
        Settings()

    assert "AUTH_SECRET_KEY must have at least 32 characters" in str(error.value)
    assert "twenty-char-secret!!" not in str(error.value)


def test_accepts_a_secret_key_of_32_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SECRET_KEY", "k" * 32)

    assert Settings().auth_secret_key.get_secret_value() == "k" * 32


def test_never_shows_the_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SECRET_KEY", SECRET_KEY)
    monkeypatch.setenv("PORT", "abc")

    with pytest.raises(ValidationError) as error:
        Settings()

    assert SECRET_KEY not in str(error.value)
    monkeypatch.delenv("PORT")
    assert SECRET_KEY not in repr(Settings())


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_rejects_a_token_ttl_that_is_not_a_positive_number_of_seconds(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", value)

    with pytest.raises(ValidationError, match="auth_token_ttl_seconds"):
        Settings()
