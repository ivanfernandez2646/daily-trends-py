import asyncio
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup, Tag

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle

MAX_FEEDS_PER_SOURCE = 5


@dataclass(frozen=True)
class ScrapMapping:
    url: str
    source: FeedSource
    author_selector: str
    title_selector: str
    description_selector: str
    encoding: str
    """Used whatever charset the response declares."""


async def scrap_front_page(client: httpx.AsyncClient, mapping: ScrapMapping) -> list[Feed]:
    # A non-2xx answer is not an error: its body is parsed like any other page.
    response = await client.get(mapping.url, headers={"Content-Type": "text/html; charset=UTF-8"})
    html = response.content.decode(mapping.encoding, errors="replace")
    return await asyncio.to_thread(extract_feeds, html, mapping)


def extract_feeds(html: str, mapping: ScrapMapping) -> list[Feed]:
    feeds: list[Feed] = []
    for article in BeautifulSoup(html, "lxml").select("article"):
        author = _text(article, mapping.author_selector)
        title = _text(article, mapping.title_selector)
        if not author or not title:
            continue
        feeds.append(
            Feed.create(
                id=FeedId.random(),
                title=FeedTitle(title),
                description=FeedDescription(_text(article, mapping.description_selector) or None),
                author=FeedAuthor(author),
                source=mapping.source,
            )
        )
        if len(feeds) >= MAX_FEEDS_PER_SOURCE:
            break
    return feeds


def _text(article: Tag, selector: str) -> str:
    """The trimmed text of every element matching `selector`, joined; `""` when none matches."""
    return "".join(element.get_text() for element in article.select(selector)).strip()
