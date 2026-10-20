from datetime import datetime
from typing import Protocol

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle


class FeedRepository(Protocol):
    async def create(self, feed: Feed) -> None:
        """Insert a new feed; raises `FeedAlreadyExists` and changes nothing if its id is taken."""
        ...

    async def update(self, feed: Feed) -> None:
        """Replace a stored feed; raises `FeedNotFound` and inserts nothing if it is missing."""
        ...

    async def find(self, id: FeedId) -> Feed | None: ...

    async def delete(self, feed: Feed) -> None: ...

    async def search(self, criteria: FeedCriteria) -> list[Feed]: ...

    async def exists_headline(
        self, source: FeedSource, title: FeedTitle, since: datetime, until: datetime
    ) -> bool:
        """Whether a feed with this source and exact title was created in `[since, until)`."""
        ...
