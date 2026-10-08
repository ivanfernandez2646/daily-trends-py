import asyncio
import codecs
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup, Tag
from bs4.dammit import EncodingDetector

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


async def scrap_front_page(client: httpx.AsyncClient, mapping: ScrapMapping) -> list[Feed]:
    # A non-2xx answer is not an error: its body is parsed like any other page.
    response = await client.get(mapping.url)
    return await asyncio.to_thread(_extract_feeds_from_response, response, mapping)


def _extract_feeds_from_response(response: httpx.Response, mapping: ScrapMapping) -> list[Feed]:
    return extract_feeds(response.content.decode(_charset(response), errors="replace"), mapping)


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
