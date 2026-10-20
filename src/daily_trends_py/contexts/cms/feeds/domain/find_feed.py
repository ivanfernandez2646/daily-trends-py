from daily_trends_py.contexts.cms.feeds.domain.errors import FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedId


async def find_feed(repository: FeedRepository, id: FeedId) -> Feed:
    feed = await repository.find(id)
    if feed is None:
        raise FeedNotFound(id)
    return feed
