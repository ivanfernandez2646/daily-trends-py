from datetime import datetime

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria

HOME_CRITERIA: Criteria = {
    "filter": [{"source": FeedSource.EL_MUNDO}, {"source": FeedSource.EL_ESPANOL}],
    "sort": {"createdAt": "desc"},
    "limit": 10,
}


class FeedHomeSearcher:
    def __init__(
        self, repository: FeedRepository, refresher: FeedHomeRefresher, clock: Clock
    ) -> None:
        self._repository = repository
        self._refresher = refresher
        self._clock = clock

    async def execute(self) -> list[Feed]:
        feeds = await self._repository.search(HOME_CRITERIA)
        if feeds and self._is_from_a_previous_day(feeds[0]):
            self._refresher.request()
        return feeds

    def _is_from_a_previous_day(self, feed: Feed) -> bool:
        now = self._clock.now()
        # A date stored without an offset is read as local time.
        created_at = datetime.fromisoformat(feed.created_at.value).astimezone(now.tzinfo)
        return created_at.date() < now.date()
