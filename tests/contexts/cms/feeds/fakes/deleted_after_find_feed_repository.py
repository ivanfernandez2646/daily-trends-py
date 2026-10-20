from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


class DeletedAfterFindFeedRepository(InMemoryFeedRepository):
    """Another request deletes each feed right after `find` returns it."""

    async def find(self, id: FeedId) -> Feed | None:
        feed = await super().find(id)
        if feed is not None:
            await self.delete(feed)
        return feed
