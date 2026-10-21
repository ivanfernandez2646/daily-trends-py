import asyncio

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order

HOME_SOURCES = (
    FeedSource.EL_MUNDO,
    FeedSource.EL_ESPANOL,
    FeedSource.EL_CONFIDENCIAL,
    FeedSource.LA_RAZON,
    FeedSource.LA_VANGUARDIA,
)
FEEDS_PER_SOURCE = 2
HOME_LIMIT = 10

_NEWEST_FIRST = Order("created_at", "desc")


class FeedHomeSearcher:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Feed]:
        """The newest feeds of each home source, filled with the newest of any of them."""
        *per_source, newest = await asyncio.gather(
            *(
                self._repository.search(
                    FeedCriteria(
                        filters=(Filter("source", source),),
                        order=_NEWEST_FIRST,
                        limit=FEEDS_PER_SOURCE,
                    )
                )
                for source in HOME_SOURCES
            ),
            self._repository.search(
                FeedCriteria(
                    filters=tuple(Filter("source", source) for source in HOME_SOURCES),
                    order=_NEWEST_FIRST,
                    limit=HOME_LIMIT,
                )
            ),
        )
        picked = [feed for source_feeds in per_source for feed in source_feeds]
        picked_ids = {feed.id for feed in picked}
        # At most `len(picked)` of the newest feeds were picked, so enough are left to fill.
        fill = [feed for feed in newest if feed.id not in picked_ids]
        feeds = [*picked, *fill[: HOME_LIMIT - len(picked)]]
        return sorted(feeds, key=lambda feed: feed.created_at.value, reverse=True)
