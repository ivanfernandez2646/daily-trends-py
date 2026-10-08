from datetime import UTC, datetime

from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.front_page import (
    ScrapMapping,
    extract_feeds,
)

MAPPING = ScrapMapping(
    url="https://news.example/",
    source=FeedSource.EL_ESPANOL,
    author_selector=".author",
    title_selector=".title",
    description_selector=".description",
    encoding="utf-8",
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
