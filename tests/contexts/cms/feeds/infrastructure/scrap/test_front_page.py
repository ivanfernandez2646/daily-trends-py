from datetime import UTC, datetime

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.front_page import (
    ScrapMapping,
    extract_feeds,
    scrap_front_page,
)

MAPPING = ScrapMapping(
    url="https://news.example/",
    source=FeedSource.EL_ESPANOL,
    author_selector=".author",
    title_selector=".title",
    description_selector=".description",
)


def _to_millis(moment: datetime) -> datetime:
    """`createdAt` is stored with millisecond precision."""
    return moment.replace(microsecond=moment.microsecond // 1000 * 1000)


def _article(author: str = "Ana", title: str = "A title", description: str = "") -> str:
    return (
        f'<article><span class="author">{author}</span><h2 class="title">{title}</h2>'
        f'<p class="description">{description}</p></article>'
    )


def test_extracts_trimmed_new_feeds_in_document_order() -> None:
    html = _article(" Ana ", "\n First title ", "  A summary ") + _article("Luis", "Second")
    before = datetime.now(UTC)

    feeds = extract_feeds(html, MAPPING)

    after = datetime.now(UTC)
    first, second = (feed.to_primitives() for feed in feeds)
    assert (first["author"], first["title"], first["description"]) == (
        "Ana",
        "First title",
        "A summary",
    )
    assert (second["author"], second["title"]) == ("Luis", "Second")
    for primitives in (first, second):
        FeedId(primitives["id"])
        assert primitives["source"] == FeedSource.EL_ESPANOL
        assert _to_millis(before) <= datetime.fromisoformat(primitives["createdAt"]) <= after
        assert primitives["updatedAt"] is None
    assert first["id"] != second["id"]


def test_skips_articles_without_author_or_title() -> None:
    html = (
        _article(author="  ")
        + _article(title="")
        + "<article><h2 class='title'>No author element</h2></article>"
        + _article("Ana", "Kept")
    )

    feeds = extract_feeds(html, MAPPING)

    assert [feed.title.value for feed in feeds] == ["Kept"]


def test_stops_at_five_feeds() -> None:
    html = "".join(_article(title=f"Title {index}") for index in range(7))

    feeds = extract_feeds(html, MAPPING)

    assert [feed.title.value for feed in feeds] == [f"Title {index}" for index in range(5)]


def test_stores_a_missing_or_blank_description_as_null() -> None:
    html = (
        "<article><span class='author'>Ana</span><h2 class='title'>No description</h2></article>"
        + _article(title="Blank description", description="  \n ")
    )

    feeds = extract_feeds(html, MAPPING)

    assert [feed.description.value for feed in feeds] == [None, None]


def test_joins_the_text_of_every_match() -> None:
    html = (
        "<article><span class='author'>Ana</span> <span class='author'>Luis</span>"
        "<h2 class='title'>A <b>bold</b> title</h2></article>"
    )

    [feed] = extract_feeds(html, MAPPING)

    assert (feed.author.value, feed.title.value) == ("AnaLuis", "A bold title")


def test_extracts_nothing_from_a_page_without_articles() -> None:
    assert extract_feeds("<html><p>Please enable JS</p></html>", MAPPING) == []


def _page(title: str, meta_charset: str | None = None) -> str:
    meta = f'<meta charset="{meta_charset}">' if meta_charset else ""
    return f"<html><head>{meta}</head><body>{_article(title=title)}</body></html>"


async def _scrap_titles(response: httpx.Response) -> list[str | None]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
        feeds = await scrap_front_page(client, MAPPING)
    return [feed.title.value for feed in feeds]


async def test_decodes_the_page_with_the_charset_of_the_content_type_header() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=iso-8859-15"},
        content=_page("Cuesta 5 €").encode("iso-8859-15"),
    )

    assert await _scrap_titles(response) == ["Cuesta 5 €"]


async def test_decodes_the_page_with_its_meta_charset_when_the_header_declares_none() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html"},
        content=_page("Cuesta 5 €", meta_charset="iso-8859-15").encode("iso-8859-15"),
    )

    assert await _scrap_titles(response) == ["Cuesta 5 €"]


async def test_decodes_the_page_as_utf_8_when_nothing_declares_a_charset() -> None:
    response = httpx.Response(200, content=_page("España").encode())

    assert await _scrap_titles(response) == ["España"]


async def test_prefers_the_header_charset_over_the_meta_charset() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=iso-8859-15"},
        content=_page("Cuesta 5 €", meta_charset="utf-8").encode("iso-8859-15"),
    )

    assert await _scrap_titles(response) == ["Cuesta 5 €"]


async def test_ignores_an_unknown_header_charset() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=not-a-charset"},
        content=_page("Cuesta 5 €", meta_charset="iso-8859-15").encode("iso-8859-15"),
    )

    assert await _scrap_titles(response) == ["Cuesta 5 €"]


async def test_requests_the_page_without_a_content_type_header() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        await scrap_front_page(client, MAPPING)

    [request] = requests
    assert str(request.url) == "https://news.example/"
    assert "Content-Type" not in request.headers


async def test_fails_when_the_request_times_out() -> None:
    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("The site never answered", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(time_out)) as client:
        with pytest.raises(httpx.ReadTimeout):
            await scrap_front_page(client, MAPPING)
