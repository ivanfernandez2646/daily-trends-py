from dataclasses import dataclass, fields
from typing import ClassVar

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria


@dataclass(frozen=True)
class FeedCriteria(Criteria):
    # Only constructor fields: the aggregate's own bookkeeping is not a feed field.
    FIELDS: ClassVar[frozenset[str]] = frozenset(field.name for field in fields(Feed) if field.init)
