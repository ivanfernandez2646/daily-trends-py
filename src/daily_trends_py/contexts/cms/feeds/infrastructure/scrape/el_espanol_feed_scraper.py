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
    url="https://www.elespanol.com/",
    source=FeedSource.EL_ESPANOL,
    author_selector=".art__author",
    title_selector=".art__title",
    description_selector=".art__subtitle",
    categories=categories_by_section(
        {
            FeedCategory.POLITICS: ("espana", "politica"),
            FeedCategory.INTERNATIONAL: ("mundo",),
            FeedCategory.ECONOMY: ("invertia",),
            FeedCategory.SOCIETY: (
                "sociedad",
                "madrid",
                "valencia",
                "cataluna",
                "andalucia",
                "castilla-y-leon",
            ),
            FeedCategory.SPORTS: ("deportes",),
            FeedCategory.CULTURE: ("cultura", "el-cultural"),
            FeedCategory.TECHNOLOGY: ("omicrono",),
            FeedCategory.SCIENCE: ("ciencia",),
            FeedCategory.HEALTH: ("salud",),
            FeedCategory.OPINION: ("opinion",),
        }
    ),
)


class ElEspanolFeedScraper:
    def __init__(self, client: httpx.AsyncClient, clock: Clock) -> None:
        self._client = client
        self._clock = clock

    async def scrape(self) -> list[Feed]:
        return await scrape_front_page(self._client, _MAPPING, self._clock)
