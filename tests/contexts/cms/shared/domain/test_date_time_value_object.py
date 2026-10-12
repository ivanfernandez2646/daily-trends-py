from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

import pytest

from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    DateTimeValueObject,
    RequiredDateTimeValueObject,
)
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


@dataclass(frozen=True)
class DummyDateTime(DateTimeValueObject):
    pass


@dataclass(frozen=True)
class DummyRequiredDateTime(RequiredDateTimeValueObject):
    pass


def test_date_time_stores_an_aware_date_time_in_utc() -> None:
    value = datetime(2026, 10, 9, 10, 0, tzinfo=timezone(timedelta(hours=2)))

    stored = DummyRequiredDateTime(value).value

    assert stored == datetime(2026, 10, 9, 8, 0, tzinfo=UTC)
    assert stored.tzinfo is UTC


def test_date_time_keeps_only_milliseconds() -> None:
    value = datetime(2026, 10, 9, 8, 0, 0, 123_456, tzinfo=UTC)

    assert DummyRequiredDateTime(value).value == datetime(2026, 10, 9, 8, 0, 0, 123_000, tzinfo=UTC)


def test_optional_date_time_accepts_none() -> None:
    assert DummyDateTime(None).value is None


@pytest.mark.parametrize(
    ("value", "rendered"),
    [
        pytest.param("2026-10-07T12:00:00.000Z", "2026-10-07T12:00:00.000Z", id="ISO string"),
        pytest.param("not-a-date", "not-a-date", id="text"),
        pytest.param(1_760_000_000_000, "1760000000000", id="number"),
        pytest.param(datetime(2026, 10, 7, 12, 0), "2026-10-07 12:00:00", id="naive date-time"),
    ],
)
def test_date_time_rejects_anything_but_an_aware_date_time(value: object, rendered: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        DummyDateTime(value)  # pyright: ignore[reportArgumentType]

    assert str(error.value) == f"<DummyDateTime> does not allow the value <{rendered}>"


def test_required_date_time_rejects_none() -> None:
    with pytest.raises(InvalidArgumentError) as error:
        DummyRequiredDateTime(None)  # pyright: ignore[reportArgumentType]

    assert str(error.value) == "<DummyRequiredDateTime> does not allow the value <None>"


def test_now_is_the_current_utc_instant_with_milliseconds() -> None:
    before = datetime.now(UTC)

    now = DummyRequiredDateTime.now()

    assert isinstance(now, DummyRequiredDateTime)
    assert now.value.tzinfo is UTC
    assert now.value.microsecond % 1000 == 0
    assert before - timedelta(milliseconds=1) <= now.value <= datetime.now(UTC)


def test_date_times_with_the_same_instant_are_equal() -> None:
    value = MotherCreator.date_time()

    assert DummyRequiredDateTime(value) == DummyRequiredDateTime(value.astimezone())
    assert DummyDateTime(value) != DummyDateTime(None)
