from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, cast

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_already_exists import FeedAlreadyExists
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

_PRIMITIVE_NAMES = {"created_at": "createdAt", "updated_at": "updatedAt"}


class InMemoryFeedRepository:
    def __init__(self, feeds: list[Feed] | None = None) -> None:
        self._feeds = {feed.id.value: feed for feed in feeds or []}
        self.created: list[Feed] = []
        self.updated: list[Feed] = []
        self.deleted: list[Feed] = []
        self.searched_ids: list[FeedId] = []

    async def create(self, feed: Feed) -> None:
        if feed.id.value in self._feeds:
            raise FeedAlreadyExists(feed.id)
        self._feeds[feed.id.value] = feed
        self.created.append(feed)

    async def update(self, feed: Feed) -> None:
        if feed.id.value not in self._feeds:
            raise FeedNotFound(feed.id)
        self._feeds[feed.id.value] = feed
        self.updated.append(feed)

    async def find(self, id: FeedId) -> Feed | None:
        self.searched_ids.append(id)
        return self._feeds.get(id.value)

    async def delete(self, feed: Feed) -> None:
        self._feeds.pop(feed.id.value, None)
        self.deleted.append(feed)

    async def search(self, criteria: FeedCriteria) -> list[Feed]:
        feeds = [
            feed
            for feed in self._feeds.values()
            if not criteria.filters
            or any(_value(feed, f.field) == f.value for f in criteria.filters)
        ]
        if criteria.order is not None:
            field = criteria.order.field
            # Like Mongo, a null value sorts before any other value in ascending order.
            feeds.sort(
                key=lambda feed: (_value(feed, field) is not None, _sortable(feed, field)),
                reverse=criteria.order.direction == "desc",
            )
        return feeds if criteria.limit is None else feeds[: criteria.limit]

    async def exists_headline(
        self, source: FeedSource, title: FeedTitle, since: datetime, until: datetime
    ) -> bool:
        return any(
            feed.source == source and feed.title == title and since <= feed.created_at.value < until
            for feed in self._feeds.values()
        )


def _value(feed: Feed, field: str) -> object:
    primitives = cast(Mapping[str, object], feed.to_primitives())
    return primitives[_PRIMITIVE_NAMES.get(field, field)]


def _sortable(feed: Feed, field: str) -> SupportsRichComparison:
    value = _value(feed, field)
    return cast("SupportsRichComparison", "" if value is None else value)
