from dataclasses import dataclass

from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    DateTimeValueObject,
)


@dataclass(frozen=True)
class FeedUpdatedAt(DateTimeValueObject):
    pass
