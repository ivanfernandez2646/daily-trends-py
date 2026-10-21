import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta

from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scraper import FeedScraper

logger = logging.getLogger(__name__)


async def _sleep(interval: timedelta) -> None:
    await asyncio.sleep(interval.total_seconds())


class FeedScrapeScheduler:
    """Scrapes at once, then one interval after each run ends or is skipped, in the background."""

    def __init__(
        self,
        scraper: FeedScraper,
        interval: timedelta,
        wait: Callable[[timedelta], Awaitable[None]] = _sleep,
    ) -> None:
        self._scraper = scraper
        self._interval = interval
        self._wait = wait
        # The event loop keeps only weak references to tasks.
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_forever())

    async def aclose(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.wait({self._task})

    async def _run_forever(self) -> None:
        while True:
            await self._run()
            await self._wait(self._interval)

    async def _run(self) -> None:
        # A due run is dropped rather than queued: the run in progress already refreshes the feeds.
        if self._scraper.is_running:
            logger.info("Scheduled scraping skipped: another scraping run is in progress")
            return
        try:
            feeds = await self._scraper.execute()
        except Exception:
            logger.exception("Scheduled scraping failed")
            return
        logger.info("Scheduled scraping saved %d feeds", len(feeds))
