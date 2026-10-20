import httpx

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.front_page import (
    ScrapeMapping,
    scrape_front_page,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock

_MAPPING = ScrapeMapping(
    url="https://www.larazon.es/",
    source=FeedSource.LA_RAZON,
    author_selector=".article__author",
    title_selector=".article__title",
    description_selector=".article__summary",
)


class LaRazonFeedScraper:
    def __init__(self, client: httpx.AsyncClient, clock: Clock) -> None:
        self._client = client
        self._clock = clock

    async def scrape(self) -> list[Feed]:
        return await scrape_front_page(self._client, _MAPPING, self._clock)
