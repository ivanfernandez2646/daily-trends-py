from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.la_vanguardia_feed_scraper import (
    LaVanguardiaFeedScraper,
)
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock
from tests.scrape_fixtures import FrontPagesTransport

NOW = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)


@pytest.fixture
def transport() -> FrontPagesTransport:
    return FrontPagesTransport()


@pytest.fixture
async def client(transport: FrontPagesTransport) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=transport) as client:
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
    await LaVanguardiaFeedScraper(client, FixedClock(NOW)).scrape()

    [request] = transport.requests
    assert str(request.url) == "https://www.lavanguardia.com/"


async def test_scrapes_five_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await LaVanguardiaFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("Eusebio Ejemplo | París", "Villaejemplo estrena un festival de cine al aire libre"),
        ("Í. Prueba", '"Plantaremos mil árboles este invierno", promete el alcalde'),
        ("Ramón Ficticio", "El equipo de baloncesto asciende de categoría"),
        ("Lucía Muestra", "Abre la primera librería del barrio"),
        ("Óscar Inventado", "La piscina municipal amplía su temporada"),
    ]
    assert [feed.description.value for feed in feeds] == [
        "Las proyecciones serán gratuitas durante todo agosto.",
        None,
        None,
        None,
        None,
    ]
    assert {feed.source for feed in feeds} == {FeedSource.LA_VANGUARDIA}
    _assert_each_feed_was_created_once_now(feeds)


@pytest.mark.network
async def test_scrapes_five_feeds_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await LaVanguardiaFeedScraper(client, FixedClock(NOW)).scrape()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.LA_VANGUARDIA
        assert feed.author.value
        assert feed.title.value
        assert feed.description.value != ""
