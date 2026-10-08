from typing import TypedDict

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.feeds.domain.find_feed import find_feed
from daily_trends_py.contexts.cms.shared.domain.raw_value import MISSING


class FeedUpdaterProps(TypedDict):
    """Raw input: each value may be of any type, or `MISSING` when it was not sent."""

    id: object
    title: object
    description: object


class FeedUpdater:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self, props: FeedUpdaterProps) -> Feed:
        feed = await find_feed(self._repository, FeedId.from_raw(props["id"]))
        title = None if props["title"] is MISSING else FeedTitle.from_raw(props["title"])
        description = (
            None
            if props["description"] is MISSING
            else FeedDescription.from_raw(props["description"])
        )

        updated = feed.update(title=title, description=description)
        if updated is None:
            return feed

        await self._repository.save(updated)
        return updated
