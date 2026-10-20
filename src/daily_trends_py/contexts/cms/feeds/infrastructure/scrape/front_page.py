import asyncio
import codecs
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import httpx
from bs4 import BeautifulSoup, Tag
from bs4.dammit import EncodingDetector

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedAuthor,
    FeedDescription,
    FeedId,
    FeedSource,
    FeedTitle,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock

MAX_FEEDS_PER_SOURCE = 5


def _unchanged(text: str) -> str:
    return text


@dataclass(frozen=True)
class ScrapeMapping:
    url: str
    source: FeedSource
    author_selector: str
    title_selector: str
    description_selector: str
    clean_description: Callable[[str], str] = _unchanged


async def scrape_front_page(
    client: httpx.AsyncClient, mapping: ScrapeMapping, clock: Clock
) -> list[Feed]:
    # A non-2xx answer is not an error: its body is parsed like any other page.
    response = await client.get(mapping.url)
    return await asyncio.to_thread(_extract_feeds_from_response, response, mapping, clock.now())


def _extract_feeds_from_response(
    response: httpx.Response, mapping: ScrapeMapping, now: datetime
) -> list[Feed]:
    html = response.content.decode(_charset(response), errors="replace")
    return extract_feeds(html, mapping, now)


def _charset(response: httpx.Response) -> str:
    """The charset of the `Content-Type` header, else the document's `<meta>` one, else UTF-8."""
    declared = (
        response.charset_encoding,
        EncodingDetector.find_declared_encoding(response.content, is_html=True),
    )
    return next((charset for charset in declared if charset and _is_known(charset)), "utf-8")


def _is_known(charset: str) -> bool:
    try:
        codecs.lookup(charset)
    except LookupError:
        return False
    return True


def extract_feeds(html: str, mapping: ScrapeMapping, now: datetime) -> list[Feed]:
    feeds: list[Feed] = []
    for article in BeautifulSoup(html, "lxml").select("article"):
        author = _text(article, mapping.author_selector)
        title = _text(article, mapping.title_selector)
        if not author or not title:
            continue
        description = mapping.clean_description(_text(article, mapping.description_selector))
        feeds.append(
            Feed.create(
                id=FeedId.random(),
                title=FeedTitle(title),
                description=FeedDescription(description or None),
                author=FeedAuthor(author),
                source=mapping.source,
                now=now,
            )
        )
        if len(feeds) >= MAX_FEEDS_PER_SOURCE:
            break
    return feeds


def _text(article: Tag, selector: str) -> str:
    """The trimmed text of every element matching `selector`, joined; `""` when none matches."""
    return "".join(element.get_text() for element in article.select(selector)).strip()
