import asyncio
from datetime import timedelta


class ControlledWait:
    """A wait that records each interval and lasts until `release()`, so no test sleeps."""

    def __init__(self) -> None:
        self.intervals: list[timedelta] = []
        self._releases = 0
        self._changed = asyncio.Condition()

    async def __call__(self, interval: timedelta) -> None:
        async with self._changed:
            self.intervals.append(interval)
            self._changed.notify_all()
            number = len(self.intervals)
            await self._changed.wait_for(lambda: self._releases >= number)

    async def reached(self, waits: int) -> None:
        """Returns once `waits` waits have started."""
        async with self._changed:
            await self._changed.wait_for(lambda: len(self.intervals) >= waits)

    async def release(self) -> None:
        """Ends the oldest wait that has not ended yet, or the next one to start."""
        async with self._changed:
            self._releases += 1
            self._changed.notify_all()
