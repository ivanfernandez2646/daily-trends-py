from datetime import UTC, datetime

from daily_trends_py.contexts.cms.shared.infrastructure.system_clock import SystemClock


def test_returns_the_current_time_with_a_timezone() -> None:
    before = datetime.now(UTC)

    now = SystemClock().now()

    after = datetime.now(UTC)
    assert now.tzinfo is not None
    assert before <= now <= after
