from datetime import date
from typing import Protocol

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria


class FeedRepository(Protocol):
    async def save(self, feed: Feed) -> None: ...

    async def find(self, id: FeedId) -> Feed | None: ...

    async def delete(self, feed: Feed) -> None: ...

    async def search(self, criteria: Criteria | None = None) -> list[Feed]: ...

    async def exists_headline(self, source: FeedSource, title: FeedTitle, day: date) -> bool:
        """Whether a feed with this source and exact title was created on this UTC day."""
        ...
