from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.el_confidencial_feed_scraper import (
    ElConfidencialFeedScraper,
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
    await ElConfidencialFeedScraper(client, FixedClock(NOW)).scrape()

    [request] = transport.requests
    assert str(request.url) == "https://www.elconfidencial.com/"


async def test_scrapes_five_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await ElConfidencialFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("Marcos Ejemplo. Barcelona", "El ayuntamiento de Villaejemplo aprueba sus presupuestos"),
        ("Í. Prueba / J. Muestra", '"Abriremos el mercado los domingos", anuncia el alcalde'),
        ("Ramón Ficticio", "La biblioteca amplía su horario en verano"),
        ("Lucía Muestra", "El club de ajedrez gana el torneo regional"),
        ("Óscar Inventado", "Los vecinos estrenan un huerto urbano"),
    ]
    assert [feed.description.value for feed in feeds] == [
        "El pleno saca adelante las cuentas con el apoyo de la oposición.",
        None,
        None,
        None,
        None,
    ]
    assert {feed.source for feed in feeds} == {FeedSource.EL_CONFIDENCIAL}
    _assert_each_feed_was_created_once_now(feeds)


@pytest.mark.network
async def test_scrapes_five_feeds_from_the_real_front_page() -> None:
    # The site answers 403 to httpx's default User-Agent, so the test sends the app's.
    async with httpx.AsyncClient(
        timeout=None, follow_redirects=True, headers={"User-Agent": "daily-trends-py"}
    ) as client:
        feeds = await ElConfidencialFeedScraper(client, FixedClock(NOW)).scrape()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.EL_CONFIDENCIAL
        assert feed.author.value
        assert feed.title.value
        assert feed.description.value != ""
