from dataclasses import dataclass

from daily_trends_py.contexts.cms.shared.domain.required_string_value_object import (
    RequiredStringValueObject,
)


@dataclass(frozen=True)
class FeedTitle(RequiredStringValueObject):
    pass
