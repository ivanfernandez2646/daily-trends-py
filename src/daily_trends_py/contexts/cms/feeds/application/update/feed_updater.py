from typing import NotRequired, TypedDict

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.feeds.domain.find_feed import find_feed


class FeedUpdaterProps(TypedDict):
    """An absent key keeps the stored value; a `None` description is assigned."""

    id: str
    title: NotRequired[str]
    description: NotRequired[str | None]


class FeedUpdater:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self, props: FeedUpdaterProps) -> Feed:
        feed = await find_feed(self._repository, FeedId(props["id"]))
        title = FeedTitle(props["title"]) if "title" in props else None
        description = FeedDescription(props["description"]) if "description" in props else None

        updated = feed.update(title=title, description=description)
        if updated is None:
            return feed

        await self._repository.save(updated)
        return updated
