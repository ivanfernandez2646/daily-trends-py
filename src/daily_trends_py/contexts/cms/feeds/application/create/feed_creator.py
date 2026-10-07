from typing import TypedDict

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_already_exists import FeedAlreadyExists
from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.shared.domain.event_bus import EventBus


class FeedCreatorProps(TypedDict):
    id: str
    title: str
    description: str | None
    author: str
    source: FeedSource


class FeedCreator:
    def __init__(self, repository: FeedRepository, event_bus: EventBus) -> None:
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, props: FeedCreatorProps) -> Feed:
        id = FeedId(props["id"])
        title = FeedTitle(props["title"])
        description = FeedDescription(props["description"])
        author = FeedAuthor(props["author"])

        if await self._repository.find(id) is not None:
            raise FeedAlreadyExists(id)

        feed = Feed.create(
            id=id, title=title, description=description, author=author, source=props["source"]
        )
        await self._repository.save(feed)
        await self._event_bus.publish(feed.pull_domain_events())
        return feed
