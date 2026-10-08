from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria


class FeedSearcher:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self, criteria: Criteria | None = None) -> list[Feed]:
        return await self._repository.search(criteria)
