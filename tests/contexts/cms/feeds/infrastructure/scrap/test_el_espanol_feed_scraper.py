from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_created_domain_event import (
    FeedCreatedDomainEvent,
)
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.el_espanol_feed_scraper import (
    ElEspanolFeedScraper,
)
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock
from tests.scrap_fixtures import FrontPagesTransport

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
    await ElEspanolFeedScraper(client, FixedClock(NOW)).scrap()

    [request] = transport.requests
    assert str(request.url) == "https://www.elespanol.com/"


async def test_scraps_five_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await ElEspanolFeedScraper(client, FixedClock(NOW)).scrap()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("Begoña Ejemplo", "Villaejemplo inaugurará su biblioteca municipal en otoño"),
        ("Í. Prueba", '"Habrá más árboles en las calles", promete la alcaldesa'),
        ("Ramón Ficticio", "El festival de cometas reúne a cien familias"),
        ("Lucía Muestra", "Los vecinos piden un carril bici junto al río"),
        ("Óscar Inventado", "La panadería más antigua celebra su centenario"),
    ]
    assert [feed.description.value for feed in feeds] == [
        "La obra costará menos de lo previsto según el pleno.",
        None,
        None,
        None,
        None,
    ]
    assert {feed.source for feed in feeds} == {FeedSource.EL_ESPANOL}
    _assert_each_feed_was_created_once_now(feeds)


async def test_scraps_nothing_from_a_page_that_blocks_the_request() -> None:
    blocked = httpx.MockTransport(
        lambda _: httpx.Response(403, html="<p>Please enable JS and disable any ad blocker</p>")
    )
    async with httpx.AsyncClient(transport=blocked) as client:
        assert await ElEspanolFeedScraper(client, FixedClock(NOW)).scrap() == []


@pytest.mark.network
async def test_scraps_five_feeds_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await ElEspanolFeedScraper(client, FixedClock(NOW)).scrap()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.EL_ESPANOL
        assert feed.author.value
        assert feed.title.value
        assert feed.description.value != ""
