from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


class FailingFeedRepository(InMemoryFeedRepository):
    """Creates normally until `creates_before_failing` feeds are stored, then raises `error`."""

    def __init__(
        self, *, creates_before_failing: int, error: Exception, feeds: list[Feed] | None = None
    ) -> None:
        super().__init__(feeds)
        self._creates_before_failing = creates_before_failing
        self._error = error

    async def create(self, feed: Feed) -> None:
        if len(self.created) >= self._creates_before_failing:
            raise self._error
        await super().create(feed)
