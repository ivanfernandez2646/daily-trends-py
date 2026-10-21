from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.el_espanol_feed_scraper import (
    ElEspanolFeedScraper,
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
    await ElEspanolFeedScraper(client, FixedClock(NOW)).scrape()

    [request] = transport.requests
    assert str(request.url) == "https://www.elespanol.com/"


async def test_scrapes_five_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await ElEspanolFeedScraper(client, FixedClock(NOW)).scrape()

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


async def test_scrapes_nothing_from_a_page_that_blocks_the_request() -> None:
    blocked = httpx.MockTransport(
        lambda _: httpx.Response(403, html="<p>Please enable JS and disable any ad blocker</p>")
    )
    async with httpx.AsyncClient(transport=blocked) as client:
        assert await ElEspanolFeedScraper(client, FixedClock(NOW)).scrape() == []


async def test_credits_each_feed_with_its_article_url_and_section_category(
    client: httpx.AsyncClient,
) -> None:
    feeds = await ElEspanolFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.url.value, feed.category) for feed in feeds] == [
        (
            "https://www.elespanol.com/espana/politica/20261020/obra-puente.html",
            FeedCategory.POLITICS,
        ),
        ("https://www.elespanol.com/madrid/20261020/arboles-calles.html", FeedCategory.SOCIETY),
        ("https://www.elespanol.com/reportajes/20261020/festival-cometas.html", FeedCategory.OTHER),
        ("https://www.elespanol.com/invertia/20261020/carril-bici.html", FeedCategory.ECONOMY),
        (
            "https://www.elespanol.com/omicrono/20261020/panaderia-centenaria.html",
            FeedCategory.TECHNOLOGY,
        ),
    ]


@pytest.mark.parametrize(
    ("section", "category"),
    [
        ("politica", FeedCategory.POLITICS),
        ("mundo", FeedCategory.INTERNATIONAL),
        ("invertia", FeedCategory.ECONOMY),
        ("valencia", FeedCategory.SOCIETY),
        ("deportes", FeedCategory.SPORTS),
        ("cultura", FeedCategory.CULTURE),
        ("omicrono", FeedCategory.TECHNOLOGY),
        ("ciencia", FeedCategory.SCIENCE),
        ("salud", FeedCategory.HEALTH),
        ("opinion", FeedCategory.OPINION),
        ("reportajes", FeedCategory.OTHER),
    ],
)
async def test_maps_its_sections_to_categories(section: str, category: FeedCategory) -> None:
    page = (
        "<article><h2 class='art__title'><a href='{href}'>A title</a></h2>"
        "<span class='art__author'>Ana</span></article>"
    ).format(href=f"/{section}/1.html")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=page))
    async with httpx.AsyncClient(transport=transport) as client:
        [feed] = await ElEspanolFeedScraper(client, FixedClock(NOW)).scrape()

    assert feed.category == category


@pytest.mark.network
async def test_scrapes_five_feeds_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await ElEspanolFeedScraper(client, FixedClock(NOW)).scrape()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.EL_ESPANOL
        assert feed.url.value is not None
        url = urlsplit(feed.url.value)
        assert url.scheme in ("http", "https")
        assert url.hostname is not None
        assert url.hostname.endswith("elespanol.com")
        assert isinstance(feed.category, FeedCategory)
        assert feed.author.value
        assert feed.title.value
        assert feed.description.value != ""
