from daily_trends_py.contexts.cms.feeds.domain.feed import Feed


class StubFeedScrap:
    def __init__(self, feeds: list[Feed] | None = None, error: Exception | None = None) -> None:
        self._feeds = feeds or []
        self._error = error
        self.calls = 0

    async def scrap(self) -> list[Feed]:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._feeds
