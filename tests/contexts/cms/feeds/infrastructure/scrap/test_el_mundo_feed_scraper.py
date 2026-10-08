from collections.abc import AsyncIterator

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.el_mundo_feed_scraper import (
    ElMundoFeedScraper,
)
from tests.scrap_fixtures import FrontPagesTransport


@pytest.fixture
def transport() -> FrontPagesTransport:
    return FrontPagesTransport()


@pytest.fixture
async def client(transport: FrontPagesTransport) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
        yield client


async def test_requests_the_front_page_as_html(
    client: httpx.AsyncClient, transport: FrontPagesTransport
) -> None:
    await ElMundoFeedScraper(client).scrap()

    first_request = transport.requests[0]
    assert str(first_request.url) == "https://elmundo.es/"
    assert first_request.headers["Content-Type"] == "text/html; charset=UTF-8"


async def test_scraps_five_feeds_decoding_the_page_as_iso_8859_1(
    client: httpx.AsyncClient,
) -> None:
    feeds = await ElMundoFeedScraper(client).scrap()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("ÁNGEL EJEMPLO", "Villaejemplo estrena un mercado de productores locales"),
        ("NOELIA PRUEBA", "Cientos de corredores participan en la carrera solidaria"),
        ("RAMÓN FICTICIO", 'El museo de juguetes abre una sala "interactiva"'),
        ("SOFÍA MUESTRA", "¿Es posible un barrio sin coches? Tres ciudades lo intentan"),
        ("IÑAKI INVENTADO", "La montaña acoge un encuentro de astronomía amateur"),
    ]
    assert {feed.source for feed in feeds} == {FeedSource.EL_MUNDO}


async def test_removes_the_last_character_of_every_description(
    client: httpx.AsyncClient,
) -> None:
    feeds = await ElMundoFeedScraper(client).scrap()

    assert [feed.description.value for feed in feeds] == [
        "Economía",
        "Deportes",
        "",
        "Urbanismo",
        "Ciencia",
    ]


@pytest.mark.network
async def test_scraps_five_feeds_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await ElMundoFeedScraper(client).scrap()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.EL_MUNDO
        assert feed.author.value
        assert feed.title.value
        texts = (feed.author.value, feed.title.value, feed.description.value or "")
        assert not any(mojibake in text for text in texts for mojibake in ("Ã", "Â"))
