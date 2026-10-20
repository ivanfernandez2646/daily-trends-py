import asyncio
import logging
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta, tzinfo

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_scrap import FeedScrap
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource

logger = logging.getLogger(__name__)


class FeedScraper:
    def __init__(
        self, repository: FeedRepository, scrapers: Sequence[FeedScrap], timezone: tzinfo
    ) -> None:
        self._repository = repository
        self._scrapers = scrapers
        self._timezone = timezone
        # Overlapping runs would each miss the other's headlines and store them twice.
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._lock.locked()

    async def execute(self) -> list[Feed]:
        async with self._lock:
            return await self._run()

    async def _run(self) -> list[Feed]:
        saved: list[Feed] = []
        saved_headlines: set[tuple[FeedSource, str | None, date]] = set()
        for feed in await self._scrap_all():
            day = feed.created_at.value.astimezone(self._timezone).date()
            headline = (feed.source, feed.title.value, day)
            if headline in saved_headlines or await self._repository.exists_headline(
                feed.source, feed.title, *self._day_bounds(day)
            ):
                continue
            await self._repository.create(feed)
            saved.append(feed)
            saved_headlines.add(headline)
        return saved

    def _day_bounds(self, day: date) -> tuple[datetime, datetime]:
        # Local midnights, so a day when clocks change lasts 23 or 25 hours.
        start = datetime.combine(day, time(), self._timezone)
        end = datetime.combine(day + timedelta(days=1), time(), self._timezone)
        return start, end

    async def _scrap_all(self) -> list[Feed]:
        results = await asyncio.gather(
            *(scraper.scrap() for scraper in self._scrapers), return_exceptions=True
        )
        feeds: list[Feed] = []
        for result in results:
            if isinstance(result, Exception):
                # A failing source must not stop the others from being saved.
                logger.warning("Scraper failed, its feeds are dropped", exc_info=result)
            elif isinstance(result, BaseException):
                raise result
            else:
                feeds.extend(result)
        return feeds
