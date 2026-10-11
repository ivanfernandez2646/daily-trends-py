from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository


class FeedSearcher:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self, criteria: FeedCriteria) -> list[Feed]:
        return await self._repository.search(criteria)
