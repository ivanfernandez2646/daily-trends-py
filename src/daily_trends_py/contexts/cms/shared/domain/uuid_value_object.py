import re
from dataclasses import dataclass
from typing import Self
from uuid import uuid4

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.required_string_value_object import (
    RequiredStringValueObject,
)

# Only versions 1 to 5 and the nil UUID are valid; newer versions (6 to 8) are rejected.
_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    r"|00000000-0000-0000-0000-000000000000",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UuidValueObject(RequiredStringValueObject):
    def __post_init__(self) -> None:
        if not _UUID.fullmatch(self.value):
            raise InvalidArgumentError(
                f"<{type(self).__name__}> does not allow the value <{self.value}>"
            )
        super().__post_init__()

    @classmethod
    def random(cls) -> Self:
        return cls(str(uuid4()))
