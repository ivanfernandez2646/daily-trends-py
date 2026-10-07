from dataclasses import dataclass

from daily_trends_py.contexts.cms.shared.domain.string_value_object import StringValueObject


@dataclass(frozen=True)
class FeedDescription(StringValueObject):
    pass
