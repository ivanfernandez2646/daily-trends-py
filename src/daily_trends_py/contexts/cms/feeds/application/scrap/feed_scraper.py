import asyncio
import dataclasses
import logging
from collections.abc import Sequence

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_scrap import FeedScrap

logger = logging.getLogger(__name__)


class FeedScraper:
    def __init__(self, repository: FeedRepository, scrapers: Sequence[FeedScrap]) -> None:
        self._repository = repository
        self._scrapers = scrapers

    async def execute(self) -> list[Feed]:
        saved: list[Feed] = []
        for feed in await self._scrap_all():
            while await self._repository.find(feed.id) is not None:
                feed = dataclasses.replace(feed, id=FeedId.random())
            await self._repository.save(feed)
            saved.append(feed)
        return saved

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
