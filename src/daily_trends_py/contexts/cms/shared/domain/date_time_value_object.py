from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.string_value_object import StringValueObject


def _ensure_is_parseable(value_object: StringValueObject, value: str) -> None:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise InvalidArgumentError(
            f"<{type(value_object).__name__}> does not allow the value <{value}>"
        ) from None


@dataclass(frozen=True)
class DateTimeValueObject(StringValueObject):
    """An ISO-8601 date-time kept as the string stored in Mongo."""

    def __post_init__(self) -> None:
        if self.value:
            _ensure_is_parseable(self, self.value)

    @classmethod
    def now(cls) -> Self:
        now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        return cls(now)


@dataclass(frozen=True)
class RequiredDateTimeValueObject(DateTimeValueObject):
    value: str

    def __post_init__(self) -> None:
        _ensure_is_parseable(self, self.value)
