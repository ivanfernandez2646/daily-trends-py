from dataclasses import dataclass

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_position import FeedPosition
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter


@dataclass(frozen=True)
class FeedPage:
    feeds: list[Feed]
    next: FeedPosition | None
    """Where the next page starts, or `None` when this page is the last one."""


class FeedSearcher:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        limit: int,
        after: FeedPosition | None = None,
        category: FeedCategory | None = None,
        source: FeedSource | None = None,
        text: str | None = None,
    ) -> FeedPage:
        """Up to `limit` feeds after `after`, newest first, of `category` and of `source`.

        With `text`, only the feeds whose title or description has any of its words.
        """
        if limit < 1:
            raise ValueError(f"<{type(self).__name__}> does not allow the limit <{limit}>")
        filters = tuple(
            Filter(field, value)
            for field, value in (("category", category), ("source", source))
            if value is not None
        )
        # One feed more than the page tells whether another page exists.
        feeds = await self._repository.search(
            FeedCriteria(
                filters=filters,
                orders=FeedCriteria.LIST_ORDER,
                limit=limit + 1,
                after=None if after is None else (after.created_at.value, after.id.value),
                text=text,
            )
        )
        page = feeds[:limit]
        has_next = len(feeds) > limit
        return FeedPage(feeds=page, next=FeedPosition.of(page[-1]) if has_next else None)
