from dataclasses import dataclass
from typing import Self

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCreatedAt, FeedId


@dataclass(frozen=True)
class FeedPosition:
    """A place in the feed list, newest first: the next page starts strictly after it.

    It is a position, not a stored feed, so it stays valid when that feed is deleted.
    """

    created_at: FeedCreatedAt
    id: FeedId

    @classmethod
    def of(cls, feed: Feed) -> Self:
        return cls(created_at=feed.created_at, id=feed.id)
