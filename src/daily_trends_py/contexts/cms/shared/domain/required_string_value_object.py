from dataclasses import dataclass
from typing import Self

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.raw_value import render_value
from daily_trends_py.contexts.cms.shared.domain.string_value_object import StringValueObject


@dataclass(frozen=True)
class RequiredStringValueObject(StringValueObject):
    value: str

    def __post_init__(self) -> None:
        if self.value.strip() == "":
            raise self._not_present(self.value)

    @classmethod
    def from_raw(cls, value: object) -> Self:
        if not isinstance(value, str):
            raise cls._not_present(value)
        return cls(value)

    @classmethod
    def _not_present(cls, value: object) -> InvalidArgumentError:
        return InvalidArgumentError(
            f"<{cls.__name__}> is mandatory. Current value: <{render_value(value)}>"
        )
