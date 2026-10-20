import httpx

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.front_page import (
    ScrapMapping,
    scrap_front_page,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock

_MAPPING = ScrapMapping(
    url="https://www.elespanol.com/",
    source=FeedSource.EL_ESPANOL,
    author_selector=".art__author",
    title_selector=".art__title",
    description_selector=".art__subtitle",
)


class ElEspanolFeedScraper:
    def __init__(self, client: httpx.AsyncClient, clock: Clock) -> None:
        self._client = client
        self._clock = clock

    async def scrap(self) -> list[Feed]:
        return await scrap_front_page(self._client, _MAPPING, self._clock)
