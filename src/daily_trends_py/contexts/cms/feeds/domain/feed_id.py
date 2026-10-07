from dataclasses import dataclass

from daily_trends_py.contexts.cms.shared.domain.uuid_value_object import UuidValueObject


@dataclass(frozen=True)
class FeedId(UuidValueObject):
    pass
