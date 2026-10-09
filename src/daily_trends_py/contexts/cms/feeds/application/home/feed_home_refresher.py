import asyncio
import logging
from datetime import timedelta

from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.shared.domain.clock import Clock

logger = logging.getLogger(__name__)


class FeedHomeRefresher:
    """Scrapes a stale front page in the background, one run at a time."""

    def __init__(self, scraper: FeedScraper, clock: Clock, cooldown: timedelta) -> None:
        self._scraper = scraper
        self._clock = clock
        self._cooldown = cooldown
        # The event loop keeps only weak references to tasks.
        self._task: asyncio.Task[None] | None = None

    def request(self) -> None:
        if self._task is not None or self._scraper.is_running:
            return
        self._task = asyncio.create_task(self._run())
        self._task.add_done_callback(self._forget)

    async def join(self) -> None:
        if self._task is not None:
            await asyncio.wait({self._task})

    async def aclose(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.wait({self._task})

    async def _run(self) -> None:
        try:
            await self._scraper.execute()
        except Exception:
            logger.exception("Background front page scraping failed")

    def _forget(self, task: asyncio.Task[None]) -> None:
        if self._task is task:
            self._task = None
