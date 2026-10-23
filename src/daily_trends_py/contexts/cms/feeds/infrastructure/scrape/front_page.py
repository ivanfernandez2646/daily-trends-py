import asyncio
import codecs
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag
from bs4.dammit import EncodingDetector

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedAuthor,
    FeedCategory,
    FeedDescription,
    FeedId,
    FeedSource,
    FeedTitle,
    FeedUrl,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)

MAX_FEEDS_PER_SOURCE = 15
MAX_FEEDS_PER_CATEGORY = 2


def _unchanged(text: str) -> str:
    return text


def categories_by_section(
    sections: Mapping[FeedCategory, Sequence[str]],
) -> Mapping[str, FeedCategory]:
    """Invert a category -> sections table into the section lookup `ScrapeMapping` takes."""
    return {section: category for category, names in sections.items() for section in names}


@dataclass(frozen=True)
class ScrapeMapping:
    url: str
    source: FeedSource
    author_selector: str
    title_selector: str
    description_selector: str
    # The first segment of an article's URL path, lowercased; any other section is `OTHER`.
    categories: Mapping[str, FeedCategory]
    clean_description: Callable[[str], str] = _unchanged


@dataclass(frozen=True)
class _Teaser:
    """A usable article as the front page shows it, before it is selected and becomes a feed."""

    author: str
    title: str
    description: str
    url: FeedUrl
    category: FeedCategory


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
    # Relative links belong to the page that was served, after any redirect.
    return extract_feeds(html, mapping, now, str(response.url))


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


def extract_feeds(html: str, mapping: ScrapeMapping, now: datetime, page_url: str) -> list[Feed]:
    teasers = [
        teaser
        for article in BeautifulSoup(html, "lxml").select("article")
        if (teaser := _teaser(article, mapping, page_url)) is not None
    ]
    return [
        Feed.create(
            id=FeedId.random(),
            title=FeedTitle(teaser.title),
            description=FeedDescription(teaser.description or None),
            author=FeedAuthor(teaser.author),
            source=mapping.source,
            category=teaser.category,
            url=teaser.url,
            now=now,
        )
        for teaser in _varied(teasers)
    ]


def _teaser(article: Tag, mapping: ScrapeMapping, page_url: str) -> _Teaser | None:
    author = _text(article, mapping.author_selector)
    title = _text(article, mapping.title_selector)
    url = _article_url(article, mapping.title_selector, page_url)
    # A scraped feed always credits the article it took the headline from.
    if not author or not title or url is None:
        return None
    return _Teaser(
        author=author,
        title=title,
        description=mapping.clean_description(_text(article, mapping.description_selector)),
        url=url,
        category=_category(url, mapping.categories),
    )


def _varied(teasers: Sequence[_Teaser]) -> list[_Teaser]:
    """The first teaser of each category, then the second, up to the limit, in page order."""
    # Front pages open with one section, usually politics, so their first teasers alone repeat it.
    seen: Counter[FeedCategory] = Counter()
    candidates: list[tuple[int, int]] = []
    for position, teaser in enumerate(teasers):
        rank = seen[teaser.category]
        seen[teaser.category] += 1
        if rank < MAX_FEEDS_PER_CATEGORY:
            candidates.append((rank, position))
    selected = sorted(candidates)[:MAX_FEEDS_PER_SOURCE]
    return [teasers[position] for _, position in sorted(selected, key=lambda pair: pair[1])]


def _text(article: Tag, selector: str) -> str:
    """The trimmed text of the first element matching `selector`; `""` when none matches."""
    # Later matches belong to the related stories a teaser can carry, not to its own headline.
    element = article.select_one(selector)
    return "" if element is None else element.get_text().strip()


def _article_url(article: Tag, title_selector: str, page_url: str) -> FeedUrl | None:
    """The resolved link of the article, or `None` when it has no `http(s)` one."""
    link = _link(article, title_selector)
    href = "" if link is None else str(link["href"]).strip()
    if not href:
        return None
    try:
        return FeedUrl(urljoin(page_url, href))
    except InvalidArgumentError:
        return None


def _link(article: Tag, title_selector: str) -> Tag | None:
    """The title when it is a link, else the link around it, inside it, or first in the article."""
    title = article.select_one(title_selector)
    if title is not None:
        if title.name == "a" and title.has_attr("href"):
            return title
        # Some front pages wrap the headline in its link, after a byline that is a link too.
        around = title.find_parent("a", href=True)
        if around is not None and any(parent is article for parent in around.parents):
            return around
        inside = title.select_one("a[href]")
        if inside is not None:
            return inside
    return article.select_one("a[href]")


def _category(url: FeedUrl, categories: Mapping[str, FeedCategory]) -> FeedCategory:
    path = urlsplit(url.value or "").path
    first_segment = path.split("/")[1] if path.startswith("/") else ""
    return categories.get(first_segment.lower(), FeedCategory.OTHER)
