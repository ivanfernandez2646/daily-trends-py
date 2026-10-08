from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria


class InMemoryFeedRepository:
    def __init__(self, feeds: list[Feed] | None = None) -> None:
        self._feeds = {feed.id.value: feed for feed in feeds or []}
        self.saved: list[Feed] = []
        self.searched_ids: list[FeedId] = []
        self.searched_criteria: list[Criteria | None] = []

    async def save(self, feed: Feed) -> None:
        self._feeds[feed.id.value] = feed
        self.saved.append(feed)

    async def find(self, id: FeedId) -> Feed | None:
        self.searched_ids.append(id)
        return self._feeds.get(id.value)

    async def search(self, criteria: Criteria | None = None) -> list[Feed]:
        self.searched_criteria.append(criteria)
        return list(self._feeds.values())
