from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedAuthor,
    FeedCategory,
    FeedDescription,
    FeedId,
    FeedSource,
    FeedTitle,
    FeedUrl,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.shared.domain.event_bus import EventBus


class FeedCreator:
    def __init__(self, repository: FeedRepository, event_bus: EventBus, clock: Clock) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._clock = clock

    async def execute(
        self,
        *,
        id: str,
        title: str,
        description: str | None,
        author: str,
        source: FeedSource,
        category: FeedCategory,
    ) -> Feed:
        feed = Feed.create(
            id=FeedId(id),
            title=FeedTitle(title),
            description=FeedDescription(description),
            author=FeedAuthor(author),
            source=source,
            category=category,
            # A feed written in the CMS has no external article to link to.
            url=FeedUrl(None),
            now=self._clock.now(),
        )
        await self._repository.create(feed)
        await self._event_bus.publish(feed.pull_domain_events())
        return feed
