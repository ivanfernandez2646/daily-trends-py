from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.find_feed import find_feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedId


class FeedFinder:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self, id: FeedId) -> Feed:
        return await find_feed(self._repository, id)
