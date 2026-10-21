import httpx

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.front_page import (
    ScrapeMapping,
    categories_by_section,
    scrape_front_page,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock


def _without_trailing_period(kicker: str) -> str:
    """Kickers read like `Crucigrama.`, a label rather than a sentence."""
    return kicker.removesuffix(".")


_MAPPING = ScrapeMapping(
    url="https://elmundo.es/",
    source=FeedSource.EL_MUNDO,
    author_selector=".ue-c-cover-content__byline-name .ue-c-cover-content__link",
    title_selector=".ue-c-cover-content__headline",
    description_selector=".ue-c-cover-content__kicker",
    categories=categories_by_section(
        {
            FeedCategory.POLITICS: ("espana", "elecciones"),
            FeedCategory.INTERNATIONAL: ("internacional",),
            FeedCategory.ECONOMY: ("economia",),
            FeedCategory.SOCIETY: (
                "sociedad",
                "madrid",
                "cataluna",
                "andalucia",
                "comunidad-valenciana",
                "castilla-y-leon",
                "baleares",
            ),
            FeedCategory.SPORTS: ("deportes",),
            FeedCategory.CULTURE: ("cultura", "television"),
            FeedCategory.TECHNOLOGY: ("tecnologia",),
            FeedCategory.SCIENCE: ("ciencia",),
            FeedCategory.HEALTH: ("salud",),
            FeedCategory.OPINION: ("opinion",),
        }
    ),
    clean_description=_without_trailing_period,
)


class ElMundoFeedScraper:
    def __init__(self, client: httpx.AsyncClient, clock: Clock) -> None:
        self._client = client
        self._clock = clock

    async def scrape(self) -> list[Feed]:
        return await scrape_front_page(self._client, _MAPPING, self._clock)
