from dataclasses import dataclass

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.string_value_object import StringValueObject


@dataclass(frozen=True)
class RequiredStringValueObject(StringValueObject):
    value: str

    def __post_init__(self) -> None:
        if self.value.strip() == "":
            raise InvalidArgumentError(
                f"<{type(self).__name__}> is mandatory. Current value: <{self.value}>"
            )
