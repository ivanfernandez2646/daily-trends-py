import dataclasses

import httpx

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.front_page import (
    ScrapMapping,
    scrap_front_page,
)

_MAPPING = ScrapMapping(
    url="https://elmundo.es/",
    source=FeedSource.EL_MUNDO,
    author_selector=".ue-c-cover-content__byline-name .ue-c-cover-content__link",
    title_selector=".ue-c-cover-content__headline",
    description_selector=".ue-c-cover-content__kicker",
    # Always iso-8859-1, whatever charset the page declares: a known defect kept (#8).
    encoding="iso-8859-1",
)


class ElMundoFeedScraper:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def scrap(self) -> list[Feed]:
        feeds = await scrap_front_page(self._client, _MAPPING)
        return [_without_last_description_character(feed) for feed in feeds]


def _without_last_description_character(feed: Feed) -> Feed:
    """The kicker usually ends with a period, but the last character is removed even when it
    is not one: a known defect kept (#8)."""
    description = feed.description.value
    if description is None:
        return feed
    return dataclasses.replace(feed, description=FeedDescription(description[:-1]))
