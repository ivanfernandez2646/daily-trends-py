from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.raw_value import render_value


def _to_stored_instant(value_object: DateTimeValueObject, value: object) -> datetime:
    """The UTC instant with millisecond precision, the most that storage keeps."""
    if not isinstance(value, datetime) or value.utcoffset() is None:
        rendered = str(value) if isinstance(value, datetime) else render_value(value)
        raise InvalidArgumentError(
            f"<{type(value_object).__name__}> does not allow the value <{rendered}>"
        )
    instant = value.astimezone(UTC)
    return instant.replace(microsecond=instant.microsecond // 1000 * 1000)


@dataclass(frozen=True)
class DateTimeValueObject:
    """A timezone-aware instant, kept in UTC."""

    value: datetime | None

    def __post_init__(self) -> None:
        if self.value is not None:
            object.__setattr__(self, "value", _to_stored_instant(self, self.value))

    @classmethod
    def now(cls) -> Self:
        return cls(datetime.now(UTC))


@dataclass(frozen=True)
class RequiredDateTimeValueObject(DateTimeValueObject):
    value: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _to_stored_instant(self, self.value))
