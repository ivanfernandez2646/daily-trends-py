import httpx

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.front_page import (
    ScrapeMapping,
    categories_by_section,
    scrape_front_page,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock

_MAPPING = ScrapeMapping(
    url="https://www.lavanguardia.com/",
    source=FeedSource.LA_VANGUARDIA,
    author_selector=".author-name, .author",
    title_selector=".title",
    description_selector=".subtitle",
    categories=categories_by_section(
        {
            FeedCategory.POLITICS: ("politica",),
            FeedCategory.INTERNATIONAL: ("internacional",),
            FeedCategory.ECONOMY: ("economia", "dinero"),
            FeedCategory.SOCIETY: ("vida", "local"),
            FeedCategory.SPORTS: ("deportes",),
            FeedCategory.CULTURE: ("cultura", "television"),
            FeedCategory.TECHNOLOGY: ("tecnologia",),
            FeedCategory.SCIENCE: ("ciencia",),
            FeedCategory.HEALTH: ("salud",),
            FeedCategory.OPINION: ("opinion",),
        }
    ),
)


class LaVanguardiaFeedScraper:
    def __init__(self, client: httpx.AsyncClient, clock: Clock) -> None:
        self._client = client
        self._clock = clock

    async def scrape(self) -> list[Feed]:
        return await scrape_front_page(self._client, _MAPPING, self._clock)
