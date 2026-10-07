import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    DateTimeValueObject,
    RequiredDateTimeValueObject,
)
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

ISO_MILLISECONDS_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")


@dataclass(frozen=True)
class DummyDateTime(DateTimeValueObject):
    pass


@dataclass(frozen=True)
class DummyRequiredDateTime(RequiredDateTimeValueObject):
    pass


@pytest.mark.parametrize("value", [None, "", "2026-10-07T12:00:00.000Z"])
def test_date_time_accepts_none_empty_or_parseable_values(value: str | None) -> None:
    assert DummyDateTime(value).value == value


def test_date_time_rejects_unparseable_values() -> None:
    value = MotherCreator.word()

    with pytest.raises(InvalidArgumentError) as error:
        DummyDateTime(value)

    # Node builds this message from `this.constructor.name` inside a static method.
    assert str(error.value) == f"<Function> doesn't allow the value <{value}>"


@pytest.mark.parametrize("value", ["", "not a date"])
def test_required_date_time_rejects_empty_or_unparseable_values(value: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        DummyRequiredDateTime(value)

    assert str(error.value) == f"<Function> doesn't allow the value <{value}>"


def test_now_is_the_current_utc_instant_in_iso_format_with_milliseconds() -> None:
    before = datetime.now(UTC)

    now = DummyRequiredDateTime.now()

    assert ISO_MILLISECONDS_UTC.fullmatch(now.value)
    parsed = datetime.fromisoformat(now.value)
    assert before - timedelta(milliseconds=1) <= parsed <= datetime.now(UTC)
    assert isinstance(now, DummyRequiredDateTime)


def test_date_times_with_the_same_value_are_equal() -> None:
    value = MotherCreator.iso_date_time()

    assert DummyRequiredDateTime(value) == DummyRequiredDateTime(value)
    assert DummyDateTime(value) != DummyDateTime(None)
