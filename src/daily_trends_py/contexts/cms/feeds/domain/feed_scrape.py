from typing import Protocol

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed


class FeedScrape(Protocol):
    async def scrape(self) -> list[Feed]: ...
