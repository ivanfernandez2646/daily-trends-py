import asyncio
import logging
from datetime import datetime, timedelta

from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.shared.domain.clock import Clock

logger = logging.getLogger(__name__)


class FeedHomeRefresher:
    """Scrapes a stale front page in the background, one run at a time, with a cooldown."""

    def __init__(self, scraper: FeedScraper, clock: Clock, cooldown: timedelta) -> None:
        self._scraper = scraper
        self._clock = clock
        self._cooldown = cooldown
        # The event loop keeps only weak references to tasks.
        self._task: asyncio.Task[None] | None = None
        self._last_run_finished_at: datetime | None = None

    def request(self) -> None:
        if self._task is not None or self._scraper.is_running or self._is_cooling_down():
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
        # Not in a `finally`: a run cancelled on shutdown did not finish.
        self._last_run_finished_at = self._clock.now()

    def _is_cooling_down(self) -> bool:
        return (
            self._last_run_finished_at is not None
            and self._clock.now() - self._last_run_finished_at < self._cooldown
        )

    def _forget(self, task: asyncio.Task[None]) -> None:
        if self._task is task:
            self._task = None
