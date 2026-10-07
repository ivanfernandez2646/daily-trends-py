from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository


async def find_feed(repository: FeedRepository, id: FeedId) -> Feed:
    feed = await repository.find(id)
    if feed is None:
        raise FeedNotFound(id)
    return feed
