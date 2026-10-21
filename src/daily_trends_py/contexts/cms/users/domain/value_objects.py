from dataclasses import dataclass, field

from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    RequiredDateTimeValueObject,
)
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.required_string_value_object import (
    RequiredStringValueObject,
)
from daily_trends_py.contexts.cms.shared.domain.string_value_object import StringValueObject
from daily_trends_py.contexts.cms.shared.domain.uuid_value_object import UuidValueObject

MIN_PASSWORD_LENGTH = 12


@dataclass(frozen=True)
class UserId(UuidValueObject):
    pass


@dataclass(frozen=True)
class UserEmail(StringValueObject):
    """Trimmed and lowercased, so two spellings of one address are the same user."""

    value: str

    def __post_init__(self) -> None:
        self._ensure_string()
        normalized = self.value.strip().lower()
        if not _is_email(normalized):
            raise InvalidArgumentError(f"<UserEmail> does not allow the value <{self.value}>")
        object.__setattr__(self, "value", normalized)


def _is_email(value: str) -> bool:
    local, at, domain = value.partition("@")
    labels = domain.split(".")
    return bool(at) and local != "" and "@" not in domain and len(labels) > 1 and all(labels)


@dataclass(frozen=True)
class UserPassword:
    """A plain password, only to create a user: never stored, and never shown in errors or logs."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if len(self.value) < MIN_PASSWORD_LENGTH:
            raise InvalidArgumentError(
                f"<UserPassword> must have at least {MIN_PASSWORD_LENGTH} characters"
            )


@dataclass(frozen=True)
class UserPasswordHash(RequiredStringValueObject):
    value: str = field(repr=False)


@dataclass(frozen=True)
class UserCreatedAt(RequiredDateTimeValueObject):
    pass
