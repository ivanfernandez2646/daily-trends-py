from typing import TypedDict, Unpack

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.find_feed import find_feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedCategory,
    FeedDescription,
    FeedId,
    FeedTitle,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock


class FeedChanges(TypedDict, total=False):
    """An absent key keeps the stored value; a `None` description is assigned."""

    title: str
    description: str | None
    category: FeedCategory


class FeedUpdater:
    def __init__(self, repository: FeedRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, id: str, **changes: Unpack[FeedChanges]) -> Feed:
        feed = await find_feed(self._repository, FeedId(id))
        title = FeedTitle(changes["title"]) if "title" in changes else None
        description = FeedDescription(changes["description"]) if "description" in changes else None

        updated = feed.update(
            now=self._clock.now(),
            title=title,
            description=description,
            category=changes.get("category"),
        )
        if updated is None:
            return feed

        await self._repository.update(updated)
        return updated
