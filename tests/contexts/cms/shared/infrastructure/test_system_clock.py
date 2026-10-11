import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.system_clock import SystemClock

TOKYO = ZoneInfo("Asia/Tokyo")


@pytest.fixture
def server_timezone(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("TZ", "America/Los_Angeles")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_returns_the_current_time() -> None:
    before = datetime.now(UTC)

    now = SystemClock(TOKYO).now()

    after = datetime.now(UTC)
    assert before <= now <= after


def test_returns_the_time_in_the_configured_timezone() -> None:
    now = SystemClock(TOKYO).now()

    assert now.tzinfo == TOKYO
    assert now.utcoffset() == timedelta(hours=9)


@pytest.mark.usefixtures("server_timezone")
def test_ignores_the_server_timezone() -> None:
    now = SystemClock(TOKYO).now()

    assert now.utcoffset() == timedelta(hours=9)
