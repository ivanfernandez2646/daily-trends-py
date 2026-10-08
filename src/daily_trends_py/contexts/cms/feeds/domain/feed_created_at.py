from dataclasses import dataclass

from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    RequiredDateTimeValueObject,
)


@dataclass(frozen=True)
class FeedCreatedAt(RequiredDateTimeValueObject):
    pass
