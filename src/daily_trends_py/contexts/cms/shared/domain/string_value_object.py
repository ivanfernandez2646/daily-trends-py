from dataclasses import dataclass
from typing import Self

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.raw_value import MISSING, render_value


@dataclass(frozen=True)
class StringValueObject:
    value: str | None

    @classmethod
    def from_raw(cls, value: object) -> Self:
        if value is MISSING or value is None:
            return cls(None)
        if not isinstance(value, str):
            raise InvalidArgumentError(
                f"<{cls.__name__}> does not allow the value <{render_value(value)}>"
            )
        return cls(value)
