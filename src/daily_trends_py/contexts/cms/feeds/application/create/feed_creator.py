from typing import TypedDict

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.shared.domain.event_bus import EventBus


class FeedCreatorProps(TypedDict):
    id: str
    title: str
    description: str | None
    author: str
    source: FeedSource


class FeedCreator:
    def __init__(self, repository: FeedRepository, event_bus: EventBus, clock: Clock) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._clock = clock

    async def execute(self, props: FeedCreatorProps) -> Feed:
        id = FeedId(props["id"])
        title = FeedTitle(props["title"])
        description = FeedDescription(props["description"])
        author = FeedAuthor(props["author"])

        feed = Feed.create(
            id=id,
            title=title,
            description=description,
            author=author,
            source=props["source"],
            now=self._clock.now(),
        )
        await self._repository.create(feed)
        await self._event_bus.publish(feed.pull_domain_events())
        return feed
