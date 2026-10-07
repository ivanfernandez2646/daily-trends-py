import pytest
from pydantic import ValidationError

from daily_trends_py.apps.cms_backend.settings import Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ENV", "MONGO_URL", "PORT"):
        monkeypatch.delenv(name, raising=False)


def test_uses_defaults_when_environment_is_empty() -> None:
    settings = Settings()

    assert settings.env == "dev"
    assert settings.mongo_url == "mongodb://localhost:27017/daily-trends"
    assert settings.port == 5000


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("MONGO_URL", "mongodb://mongo:27017/other")
    monkeypatch.setenv("PORT", "8080")

    settings = Settings()

    assert settings.env == "production"
    assert settings.mongo_url == "mongodb://mongo:27017/other"
    assert settings.port == 8080


def test_rejects_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "staging")

    with pytest.raises(ValidationError):
        Settings()
