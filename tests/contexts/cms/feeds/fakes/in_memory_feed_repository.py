import operator
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, cast

from daily_trends_py.contexts.cms.feeds.domain.errors import FeedAlreadyExists, FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedId, FeedSource, FeedTitle
from daily_trends_py.contexts.cms.shared.domain.criteria import Order

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison


class InMemoryFeedRepository:
    def __init__(self, feeds: list[Feed] | None = None) -> None:
        self._feeds = {feed.id.value: feed for feed in feeds or []}
        self.created: list[Feed] = []
        self.updated: list[Feed] = []
        self.deleted: list[Feed] = []
        self.searched_ids: list[FeedId] = []
        self.searched_criteria: list[FeedCriteria] = []

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
        self.searched_criteria.append(criteria)
        values_by_field = criteria.values_by_field()
        feeds = [
            feed
            for feed in self._feeds.values()
            if all(_value(feed, field) in values for field, values in values_by_field.items())
        ]
        if criteria.after is not None:
            feeds = [feed for feed in feeds if _is_after(feed, criteria.orders, criteria.after)]
        # A stable sort by each order from the last one sorts by all of them, the first one first.
        for order in reversed(criteria.orders):
            # Like Mongo, a null value sorts before any other value in ascending order.
            feeds.sort(
                key=lambda feed, field=order.field: (
                    _value(feed, field) is not None,
                    _sortable(feed, field),
                ),
                reverse=order.direction == "desc",
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
    return primitives[field]


def _sortable(feed: Feed, field: str) -> SupportsRichComparison:
    value = _value(feed, field)
    return cast("SupportsRichComparison", "" if value is None else value)


def _is_after(feed: Feed, orders: Sequence[Order], after: Sequence[object]) -> bool:
    for order, position in zip(orders, after, strict=True):
        value = _sortable(feed, order.field)
        bound = cast("SupportsRichComparison", position)
        if value != bound:
            return bool((operator.lt if order.direction == "desc" else operator.gt)(value, bound))
    return False
