from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


class FailingFeedRepository(InMemoryFeedRepository):
    """Saves normally until `saves_before_failing` feeds are stored, then raises `error`."""

    def __init__(
        self, *, saves_before_failing: int, error: Exception, feeds: list[Feed] | None = None
    ) -> None:
        super().__init__(feeds)
        self._saves_before_failing = saves_before_failing
        self._error = error

    async def save(self, feed: Feed) -> None:
        if len(self.saved) >= self._saves_before_failing:
            raise self._error
        await super().save(feed)
