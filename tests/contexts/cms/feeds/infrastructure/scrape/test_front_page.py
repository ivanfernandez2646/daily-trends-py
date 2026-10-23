import dataclasses
from datetime import UTC, datetime

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedCategory,
    FeedId,
    FeedSource,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.front_page import (
    ScrapeMapping,
    extract_feeds,
    scrape_front_page,
)
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock

MAPPING = ScrapeMapping(
    url="https://news.example/",
    source=FeedSource.EL_ESPANOL,
    author_selector=".author",
    title_selector=".title",
    description_selector=".description",
    categories={"deportes": FeedCategory.SPORTS, "cultura": FeedCategory.CULTURE},
)
PAGE_URL = "https://news.example/"
NOW = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)


def _article(
    author: str = "Ana",
    title: str = "A title",
    description: str = "",
    href: str = "/deportes/1.html",
) -> str:
    return (
        f'<article><span class="author">{author}</span>'
        f'<h2 class="title"><a href="{href}">{title}</a></h2>'
        f'<p class="description">{description}</p></article>'
    )


def test_extracts_trimmed_new_feeds_in_document_order() -> None:
    html = _article(" Ana ", "\n First title ", "  A summary ") + _article("Luis", "Second")

    feeds = extract_feeds(html, MAPPING, NOW, PAGE_URL)

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
        assert primitives["created_at"] == NOW
        assert primitives["updated_at"] is None
    assert first["id"] != second["id"]


def test_skips_articles_without_author_or_title() -> None:
    html = (
        _article(author="  ")
        + _article(title="")
        + "<article><h2 class='title'>No author element</h2></article>"
        + _article("Ana", "Kept")
    )

    feeds = extract_feeds(html, MAPPING, NOW, PAGE_URL)

    assert [feed.title.value for feed in feeds] == ["Kept"]


EVERY_SECTION = dataclasses.replace(
    MAPPING,
    categories={
        category.value.lower(): category
        for category in FeedCategory
        if category is not FeedCategory.OTHER
    },
)


def _in(category: FeedCategory, title: str) -> str:
    return _article(title=title, href=f"/{category.value.lower()}/{title}.html")


def _titles(html: str) -> list[str]:
    return [feed.title.value or "" for feed in extract_feeds(html, EVERY_SECTION, NOW, PAGE_URL)]


def test_selects_the_first_article_of_each_category_then_the_second_in_page_order() -> None:
    politics, sports, culture = FeedCategory.POLITICS, FeedCategory.SPORTS, FeedCategory.CULTURE
    html = (
        _in(politics, "p1")
        + _in(politics, "p2")
        + _in(sports, "s1")
        + _in(politics, "p3")
        + _in(culture, "c1")
        + _in(sports, "s2")
    )

    assert _titles(html) == ["p1", "p2", "s1", "c1", "s2"]


def test_keeps_at_most_two_feeds_of_a_category() -> None:
    html = "".join(_in(FeedCategory.POLITICS, f"p{index}") for index in range(5))

    assert _titles(html) == ["p0", "p1"]


def test_counts_every_unknown_section_as_the_same_other_category() -> None:
    html = "".join(
        _article(title=section, href=f"/{section}/1.html")
        for section in ("juegos", "papel", "viajes")
    )

    feeds = extract_feeds(html, EVERY_SECTION, NOW, PAGE_URL)

    assert [(feed.title.value, feed.category) for feed in feeds] == [
        ("juegos", FeedCategory.OTHER),
        ("papel", FeedCategory.OTHER),
    ]


def test_takes_the_first_two_of_each_category_when_every_category_has_more() -> None:
    categories = (FeedCategory.POLITICS, FeedCategory.SPORTS, FeedCategory.CULTURE)
    html = "".join(
        _in(category, f"{category.value}{index}") for category in categories for index in range(5)
    )

    assert _titles(html) == [
        f"{category.value}{index}" for category in categories for index in range(2)
    ]


def test_stops_at_fifteen_feeds_taking_the_second_round_in_page_order() -> None:
    categories = [category for category in FeedCategory if category is not FeedCategory.OTHER]
    html = "".join(
        _in(category, f"{category.value}{index}") for category in categories for index in (1, 2)
    )

    titles = _titles(html)

    seconds_taken = 15 - len(categories)
    assert titles == [
        f"{category.value}{index}"
        for position, category in enumerate(categories)
        for index in ((1, 2) if position < seconds_taken else (1,))
    ]


def test_does_not_count_unusable_articles_toward_the_quota_of_their_category() -> None:
    sports = "/deportes/1.html"
    html = (
        _article(author="", title="No author", href=sports)
        + _article(title="", href=sports)
        + _in(FeedCategory.SPORTS, "s1")
        + _in(FeedCategory.SPORTS, "s2")
    )

    assert _titles(html) == ["s1", "s2"]


def test_stores_a_missing_or_blank_description_as_null() -> None:
    html = (
        "<article><span class='author'>Ana</span>"
        "<h2 class='title'><a href='/1.html'>No description</a></h2></article>"
        + _article(title="Blank description", description="  \n ")
    )

    feeds = extract_feeds(html, MAPPING, NOW, PAGE_URL)

    assert [feed.description.value for feed in feeds] == [None, None]


def _without_exclamation(text: str) -> str:
    return text.removesuffix("!")


def test_cleans_the_description_before_creating_the_feed() -> None:
    mapping = dataclasses.replace(MAPPING, clean_description=_without_exclamation)
    html = _article(title="Cleaned", description="Wow!") + _article(
        title="Emptied", description="!"
    )

    feeds = extract_feeds(html, mapping, NOW, PAGE_URL)

    assert [feed.description.value for feed in feeds] == ["Wow", None]
    assert [len(feed.pull_domain_events()) for feed in feeds] == [1, 1]


def test_takes_the_text_of_the_first_match_only() -> None:
    # A teaser can carry related headlines and their bylines after its own.
    html = (
        "<article><span class='author'>Ana</span> <span class='author'>Luis</span>"
        "<h2 class='title'><a href='/1.html'>A <b>bold</b> title</a></h2>"
        "<h3 class='title'>A related story</h3>"
        "<p class='description'>The lead</p><p class='description'>Another lead</p></article>"
    )

    [feed] = extract_feeds(html, MAPPING, NOW, PAGE_URL)

    assert (feed.author.value, feed.title.value, feed.description.value) == (
        "Ana",
        "A bold title",
        "The lead",
    )


def test_extracts_nothing_from_a_page_without_articles() -> None:
    assert extract_feeds("<html><p>Please enable JS</p></html>", MAPPING, NOW, PAGE_URL) == []


def _url_of(article: str, page_url: str = PAGE_URL) -> str | None:
    [feed] = extract_feeds(article, MAPPING, NOW, page_url)
    return feed.url.value


@pytest.mark.parametrize(
    ("article", "url"),
    [
        pytest.param(
            "<article><span class='author'>Ana</span>"
            "<a class='title' href='/title-is-the-link.html'>A title</a></article>",
            "https://news.example/title-is-the-link.html",
            id="the title is the link",
        ),
        pytest.param(
            "<article><span class='author'>Ana</span>"
            "<a href='/around-the-title.html'><h2 class='title'>A title</h2></a></article>",
            "https://news.example/around-the-title.html",
            id="a link around the title",
        ),
        pytest.param(
            "<article><a href='/section/'>Section</a><span class='author'>Ana</span>"
            "<h2 class='title'><a href='/inside-the-title.html'>A title</a></h2></article>",
            "https://news.example/inside-the-title.html",
            id="a link inside the title before an earlier one",
        ),
        pytest.param(
            "<article><span class='author'>Ana</span><h2 class='title'>A title</h2>"
            "<a href='/first-link.html'>Read more</a><a href='/second.html'>Share</a></article>",
            "https://news.example/first-link.html",
            id="the first link in the article",
        ),
    ],
)
def test_takes_the_article_link_from_the_title_first(article: str, url: str) -> None:
    assert _url_of(article) == url


def test_does_not_take_a_byline_link_before_a_title_wrapped_in_its_link() -> None:
    article = (
        "<article><a class='author' href='/autor/ana.html'>Ana</a>"
        "<a href='/deportes/1.html'><h2 class='title'>A title</h2></a></article>"
    )

    assert _url_of(article) == "https://news.example/deportes/1.html"


@pytest.mark.parametrize(
    ("page_url", "href", "url"),
    [
        ("https://news.example/", "/deportes/1.html", "https://news.example/deportes/1.html"),
        ("https://news.example/portada/", "1.html", "https://news.example/portada/1.html"),
        ("https://news.example/", "//cdn.example/1.html", "https://cdn.example/1.html"),
        (
            "https://news.example/",
            "https://other.example/deportes/1.html",
            "https://other.example/deportes/1.html",
        ),
        (
            "https://news.example/",
            " /deportes/1.html?utm=home#comments ",
            "https://news.example/deportes/1.html?utm=home#comments",
        ),
    ],
)
def test_resolves_the_link_against_the_page_and_keeps_query_and_fragment(
    page_url: str, href: str, url: str
) -> None:
    assert _url_of(_article(href=href), page_url) == url


def test_skips_articles_without_a_usable_link_and_tries_the_next_ones() -> None:
    unusable = [
        "<article><span class='author'>Ana</span><h2 class='title'>No link</h2></article>",
        "<article><span class='author'>Ana</span><h2 class='title'><a>No href</a></h2></article>",
        _article(title="Blank", href="  "),
        _article(title="Mail", href="mailto:redaccion@news.example"),
        _article(title="Script", href="javascript:void(0)"),
        _article(title="Ftp", href="ftp://news.example/1.html"),
    ]
    html = "".join(unusable) + _article(title="Sports") + _article(title="Culture", href="/cultura")

    feeds = extract_feeds(html, MAPPING, NOW, PAGE_URL)

    assert [feed.title.value for feed in feeds] == ["Sports", "Culture"]


@pytest.mark.parametrize(
    ("href", "category"),
    [
        pytest.param("/deportes/futbol/1.html", FeedCategory.SPORTS, id="first segment"),
        pytest.param("/DEPORTES/1.html", FeedCategory.SPORTS, id="any case"),
        pytest.param("/cultura", FeedCategory.CULTURE, id="a single segment"),
        pytest.param("/juegos/crucigrama/", FeedCategory.OTHER, id="unknown section"),
        pytest.param("/1/deportes/", FeedCategory.OTHER, id="only the first segment"),
        pytest.param("/", FeedCategory.OTHER, id="an empty path"),
        pytest.param("?deportes", FeedCategory.OTHER, id="only a query"),
        pytest.param(
            "https://other.example/cultura/1.html", FeedCategory.CULTURE, id="another host"
        ),
    ],
)
def test_takes_the_category_from_the_first_segment_of_the_link_path(
    href: str, category: FeedCategory
) -> None:
    [feed] = extract_feeds(_article(href=href), MAPPING, NOW, PAGE_URL)

    assert feed.category == category


async def test_resolves_links_against_the_front_page_url_after_redirects() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.host == "news.example":
            return httpx.Response(301, headers={"Location": "https://www.news.example/"})
        return httpx.Response(200, content=_article(href="/cultura/1.html").encode())

    transport = httpx.MockTransport(handle)
    async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
        [feed] = await scrape_front_page(client, MAPPING, FixedClock(NOW))

    assert feed.url.value == "https://www.news.example/cultura/1.html"
    assert feed.category == FeedCategory.CULTURE


def _page(title: str, meta_charset: str | None = None) -> str:
    meta = f'<meta charset="{meta_charset}">' if meta_charset else ""
    return f"<html><head>{meta}</head><body>{_article(title=title)}</body></html>"


async def _scrape_titles(response: httpx.Response) -> list[str | None]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
        feeds = await scrape_front_page(client, MAPPING, FixedClock(NOW))
    return [feed.title.value for feed in feeds]


async def test_decodes_the_page_with_the_charset_of_the_content_type_header() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=iso-8859-15"},
        content=_page("Cuesta 5 €").encode("iso-8859-15"),
    )

    assert await _scrape_titles(response) == ["Cuesta 5 €"]


async def test_decodes_the_page_with_its_meta_charset_when_the_header_declares_none() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html"},
        content=_page("Cuesta 5 €", meta_charset="iso-8859-15").encode("iso-8859-15"),
    )

    assert await _scrape_titles(response) == ["Cuesta 5 €"]


async def test_decodes_the_page_as_utf_8_when_nothing_declares_a_charset() -> None:
    response = httpx.Response(200, content=_page("España").encode())

    assert await _scrape_titles(response) == ["España"]


async def test_prefers_the_header_charset_over_the_meta_charset() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=iso-8859-15"},
        content=_page("Cuesta 5 €", meta_charset="utf-8").encode("iso-8859-15"),
    )

    assert await _scrape_titles(response) == ["Cuesta 5 €"]


async def test_ignores_an_unknown_header_charset() -> None:
    response = httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=not-a-charset"},
        content=_page("Cuesta 5 €", meta_charset="iso-8859-15").encode("iso-8859-15"),
    )

    assert await _scrape_titles(response) == ["Cuesta 5 €"]


async def test_requests_the_page_without_a_content_type_header() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        await scrape_front_page(client, MAPPING, FixedClock(NOW))

    [request] = requests
    assert str(request.url) == "https://news.example/"
    assert "Content-Type" not in request.headers


async def test_fails_when_the_request_times_out() -> None:
    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("The site never answered", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(time_out)) as client:
        with pytest.raises(httpx.ReadTimeout):
            await scrape_front_page(client, MAPPING, FixedClock(NOW))
