from enum import StrEnum
from typing import Never

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)


class FeedSource(StrEnum):
    CMS = "CMS"
    EL_PAIS = "EL_PAIS"
    EL_MUNDO = "EL_MUNDO"
    EL_ESPANOL = "EL_ESPANOL"

    @classmethod
    def _missing_(cls, value: object) -> Never:
        # `Enum` raises what `_missing_` raises, so an unknown source is an invalid argument.
        raise InvalidArgumentError(f"<FeedSource> does not allow the value <{value}>")
