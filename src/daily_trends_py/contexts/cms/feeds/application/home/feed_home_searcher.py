import asyncio
from collections import Counter
from collections.abc import Sequence

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order

HOME_SOURCES = (
    FeedSource.EL_MUNDO,
    FeedSource.EL_ESPANOL,
    FeedSource.EL_CONFIDENCIAL,
    FeedSource.LA_RAZON,
    FeedSource.LA_VANGUARDIA,
)
CANDIDATES_PER_SOURCE = 15
FEEDS_PER_SOURCE = 2
FEEDS_PER_CATEGORY = 2
HOME_LIMIT = 10

_NEWEST_FIRST = Order("created_at", "desc")


class FeedHomeSearcher:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Feed]:
        """At most 2 feeds per source and per category, filled with the newest of the others."""
        per_source = await asyncio.gather(
            *(
                self._repository.search(
                    FeedCriteria(
                        filters=(Filter("source", source),),
                        orders=(_NEWEST_FIRST,),
                        limit=CANDIDATES_PER_SOURCE,
                    )
                )
                for source in HOME_SOURCES
            )
        )
        candidates = _newest_first([feed for source_feeds in per_source for feed in source_feeds])
        picked = _varied(candidates)
        picked_ids = {feed.id for feed in picked}
        fill = [feed for feed in candidates if feed.id not in picked_ids]
        return _newest_first([*picked, *fill[: HOME_LIMIT - len(picked)]])


def _varied(candidates: Sequence[Feed]) -> list[Feed]:
    # A scraping run gives a source's whole batch the same creation time, so its newest feeds
    # alone are an arbitrary pair of the batch, usually its opening political stories.
    picked: list[Feed] = []
    per_source: Counter[FeedSource] = Counter()
    per_category: Counter[FeedCategory] = Counter()
    for feed in candidates:
        if len(picked) == HOME_LIMIT:
            break
        if per_source[feed.source] < FEEDS_PER_SOURCE and (
            per_category[feed.category] < FEEDS_PER_CATEGORY
        ):
            picked.append(feed)
            per_source[feed.source] += 1
            per_category[feed.category] += 1
    return picked


def _newest_first(feeds: list[Feed]) -> list[Feed]:
    # A stable sort, so feeds created at the same time keep the order the repository gave.
    return sorted(feeds, key=lambda feed: feed.created_at.value, reverse=True)
