from typing import Protocol

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed


class FeedScrap(Protocol):
    async def scrap(self) -> list[Feed]: ...
