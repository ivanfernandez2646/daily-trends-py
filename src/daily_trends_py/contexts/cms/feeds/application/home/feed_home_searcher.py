from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria

HOME_CRITERIA: Criteria = {
    "filter": [
        {"source": FeedSource.EL_MUNDO},
        {"source": FeedSource.EL_ESPANOL},
    ],
    "sort": {"createdAt": "desc"},
    "limit": 10,
}


class FeedHomeSearcher:
    def __init__(self, repository: FeedRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Feed]:
        return await self._repository.search(HOME_CRITERIA)
