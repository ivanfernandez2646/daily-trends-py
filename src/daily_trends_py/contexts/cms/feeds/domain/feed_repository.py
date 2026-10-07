from typing import Protocol

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId


class FeedRepository(Protocol):
    async def save(self, feed: Feed) -> None: ...

    async def find(self, id: FeedId) -> Feed | None: ...
