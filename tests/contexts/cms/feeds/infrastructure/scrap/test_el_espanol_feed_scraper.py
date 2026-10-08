from collections.abc import AsyncIterator

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.el_espanol_feed_scraper import (
    ElEspanolFeedScraper,
)
from tests.scrap_fixtures import FrontPagesTransport


@pytest.fixture
def transport() -> FrontPagesTransport:
    return FrontPagesTransport()


@pytest.fixture
async def client(transport: FrontPagesTransport) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=transport) as client:
        yield client


async def test_requests_the_front_page_as_html(
    client: httpx.AsyncClient, transport: FrontPagesTransport
) -> None:
    await ElEspanolFeedScraper(client).scrap()

    [request] = transport.requests
    assert str(request.url) == "https://www.elespanol.com/"
    assert request.headers["Content-Type"] == "text/html; charset=UTF-8"


async def test_scraps_five_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await ElEspanolFeedScraper(client).scrap()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("María Peral", "Anticorrupción ve indicios pero esperará a completar las diligencias"),
        ("M. León", '"No habrá paz en las calles", dice la portavoz'),
        ("Alberto D. Prieto", "La muerte de Maricarmen tensiona el debate sobre la vivienda"),
        ("Alberto Cheli", "Los acampados de Sol piden una ley de alquileres"),
        ("Rubén Fernández", "El Gobierno estudia la primera huelga de inquilinos"),
    ]
    assert [feed.description.value for feed in feeds] == [
        "La imputación no se produciría antes del otoño.",
        "",
        "",
        "",
        "",
    ]
    assert {feed.source for feed in feeds} == {FeedSource.EL_ESPANOL}


async def test_scraps_nothing_from_a_page_that_blocks_the_request() -> None:
    blocked = httpx.MockTransport(
        lambda _: httpx.Response(403, html="<p>Please enable JS and disable any ad blocker</p>")
    )
    async with httpx.AsyncClient(transport=blocked) as client:
        assert await ElEspanolFeedScraper(client).scrap() == []


@pytest.mark.network
async def test_scraps_five_feeds_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await ElEspanolFeedScraper(client).scrap()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.EL_ESPANOL
        assert feed.author.value
        assert feed.title.value
        assert isinstance(feed.description.value, str)
