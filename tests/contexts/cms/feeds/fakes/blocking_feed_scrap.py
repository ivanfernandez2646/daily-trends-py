import asyncio

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed


class BlockingFeedScrap:
    """Waits inside `scrap()` until `release()` is called, so a test can act mid-run."""

    def __init__(self, feeds: list[Feed] | None = None) -> None:
        self._feeds = feeds or []
        self._released = asyncio.Event()
        self.started = asyncio.Event()
        self.calls = 0

    async def scrap(self) -> list[Feed]:
        self.calls += 1
        self.started.set()
        await self._released.wait()
        return self._feeds

    def release(self) -> None:
        self._released.set()
