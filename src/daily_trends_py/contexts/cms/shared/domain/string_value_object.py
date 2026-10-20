from dataclasses import dataclass

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)


@dataclass(frozen=True)
class StringValueObject:
    value: str | None

    def __post_init__(self) -> None:
        if self.value is not None:
            self._ensure_string()

    def _ensure_string(self) -> None:
        # Stored documents can hold anything, so the value is not always a string.
        value: object = self.value
        if not isinstance(value, str):
            raise InvalidArgumentError(
                f"<{type(self).__name__}> does not allow the value <{value}>"
            )
