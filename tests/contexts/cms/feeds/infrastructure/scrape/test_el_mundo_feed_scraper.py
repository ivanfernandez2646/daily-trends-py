from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.el_mundo_feed_scraper import (
    ElMundoFeedScraper,
)
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock
from tests.scrape_fixtures import FrontPagesTransport

NOW = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)


@pytest.fixture
def transport() -> FrontPagesTransport:
    return FrontPagesTransport()


@pytest.fixture
async def client(transport: FrontPagesTransport) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
        yield client


def _assert_each_feed_was_created_once_now(feeds: list[Feed]) -> None:
    for feed in feeds:
        assert feed.created_at.value == NOW
        [event] = feed.pull_domain_events()
        assert isinstance(event, FeedCreatedDomainEvent)
        assert event.aggregate_id == feed.id.value


async def test_requests_the_front_page(
    client: httpx.AsyncClient, transport: FrontPagesTransport
) -> None:
    await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    first_request = transport.requests[0]
    assert str(first_request.url) == "https://elmundo.es/"


async def test_scrapes_five_feeds_decoding_the_page_with_its_declared_charset(
    client: httpx.AsyncClient,
) -> None:
    feeds = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("ÁNGEL EJEMPLO", "Villaejemplo estrena un mercado de productores locales"),
        ("NOELIA PRUEBA", "Cientos de corredores participan en la carrera solidaria"),
        ("RAMÓN FICTICIO", 'El museo de juguetes abre una sala "interactiva"'),
        ("SOFÍA MUESTRA", "¿Es posible un barrio sin coches? Tres ciudades lo intentan"),
        ("IÑAKI INVENTADO", "La montaña acoge un encuentro de astronomía amateur"),
    ]
    assert {feed.source for feed in feeds} == {FeedSource.EL_MUNDO}
    _assert_each_feed_was_created_once_now(feeds)


async def test_removes_the_trailing_period_of_every_description_and_keeps_a_missing_one_null(
    client: httpx.AsyncClient,
) -> None:
    feeds = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert [feed.description.value for feed in feeds] == [
        "Economía",
        "Deportes",
        None,
        "Urbanismo",
        "Ciencia",
    ]


@pytest.mark.parametrize(
    ("kicker", "description"),
    [
        ("¿Qué pasa?", "¿Qué pasa?"),
        ("Sudoku...", "Sudoku.."),
        (" Crucigrama. ", "Crucigrama"),
        (".", None),
    ],
)
async def test_removes_only_one_trailing_period(kicker: str, description: str | None) -> None:
    page = (
        "<article><span class='ue-c-cover-content__kicker'>"
        f"{kicker}</span><h2 class='ue-c-cover-content__headline'>A title</h2>"
        "<span class='ue-c-cover-content__byline-name'>"
        "<a class='ue-c-cover-content__link'>Ana</a></span></article>"
    )
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=page))
    async with httpx.AsyncClient(transport=transport) as client:
        [feed] = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert feed.description.value == description
    _assert_each_feed_was_created_once_now([feed])


@pytest.mark.network
async def test_scrapes_five_feeds_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.EL_MUNDO
        assert feed.author.value
        assert feed.title.value
        texts = (feed.author.value, feed.title.value, feed.description.value or "")
        assert not any(mojibake in text for text in texts for mojibake in ("Ã", "Â"))
