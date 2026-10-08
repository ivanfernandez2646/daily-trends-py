import asyncio

import httpx

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.front_page import (
    ScrapMapping,
    extract_feeds,
    fetch_front_page,
)

_MAPPING = ScrapMapping(
    url="https://www.elespanol.com/",
    source=FeedSource.EL_ESPANOL,
    author_selector=".art__author",
    title_selector=".art__title",
    description_selector=".art__subtitle",
)


class ElEspanolFeedScraper:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def scrap(self) -> list[Feed]:
        body = await fetch_front_page(self._client, _MAPPING.url)
        # Always UTF-8, whatever charset the response declares.
        html = body.decode("utf-8", errors="replace")
        return await asyncio.to_thread(extract_feeds, html, _MAPPING)
