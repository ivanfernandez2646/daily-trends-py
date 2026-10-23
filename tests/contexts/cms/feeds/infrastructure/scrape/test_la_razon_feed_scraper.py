from collections import Counter
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.la_razon_feed_scraper import (
    LaRazonFeedScraper,
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
    await LaRazonFeedScraper(client, FixedClock(NOW)).scrape()

    [request] = transport.requests
    assert str(request.url) == "https://www.larazon.es/"


async def test_scrapes_six_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await LaRazonFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("Begoña Ejemplo", "Villaejemplo tendrá una nueva estación de tren en 2028"),
        ("Í. Prueba", '"El puerto crecerá sin perder la playa", asegura la concejala'),
        ("Ramón Ficticio", "La feria del libro bate su récord de visitantes"),
        ("Lucía Muestra", "El mercado de abastos reabre tras la reforma"),
        ("Óscar Inventado", "Un coro infantil cantará en la catedral"),
        ("Nadie", "Una noticia sin sección también se guarda"),
    ]
    assert [feed.description.value for feed in feeds] == [
        "El proyecto incluye un aparcamiento para bicicletas.",
        None,
        None,
        None,
        None,
        None,
    ]
    assert {feed.source for feed in feeds} == {FeedSource.LA_RAZON}
    _assert_each_feed_was_created_once_now(feeds)


async def test_credits_each_feed_with_its_article_url_and_section_category(
    client: httpx.AsyncClient,
) -> None:
    feeds = await LaRazonFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.url.value, feed.category) for feed in feeds] == [
        (
            "https://www.larazon.es/espana/villaejemplo-estacion-tren_2026102001.html",
            FeedCategory.POLITICS,
        ),
        ("https://www.larazon.es/andalucia/puerto-playa_2026102003.html", FeedCategory.SOCIETY),
        ("https://www.larazon.es/cultura/feria-libro-record_2026102005.html", FeedCategory.CULTURE),
        ("https://www.larazon.es/economia/mercado-abastos_2026102006.html", FeedCategory.ECONOMY),
        ("https://www.larazon.es/deportes/futbol/123.html", FeedCategory.SPORTS),
        ("https://www.larazon.es/noticia-8.html", FeedCategory.OTHER),
    ]


@pytest.mark.parametrize(
    ("section", "category"),
    [
        ("espana", FeedCategory.POLITICS),
        ("internacional", FeedCategory.INTERNATIONAL),
        ("economia", FeedCategory.ECONOMY),
        ("comunidad-valenciana", FeedCategory.SOCIETY),
        ("deportes", FeedCategory.SPORTS),
        ("cultura", FeedCategory.CULTURE),
        ("television", FeedCategory.CULTURE),
        ("tecnologia", FeedCategory.TECHNOLOGY),
        ("tecnologia-consumo", FeedCategory.TECHNOLOGY),
        ("ciencia", FeedCategory.SCIENCE),
        ("salud", FeedCategory.HEALTH),
        ("opinion", FeedCategory.OPINION),
        ("motor", FeedCategory.OTHER),
    ],
)
async def test_maps_its_sections_to_categories(section: str, category: FeedCategory) -> None:
    page = (
        "<article><h2 class='article__title'><a href='{href}'>A title</a></h2>"
        "<div class='article__author'>Ana</div></article>"
    ).format(href=f"/{section}/1.html")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=page))
    async with httpx.AsyncClient(transport=transport) as client:
        [feed] = await LaRazonFeedScraper(client, FixedClock(NOW)).scrape()

    assert feed.category == category


@pytest.mark.network
async def test_scrapes_a_varied_selection_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await LaRazonFeedScraper(client, FixedClock(NOW)).scrape()

    assert 1 <= len(feeds) <= 15
    assert max(Counter(feed.category for feed in feeds).values()) <= 2
    for feed in feeds:
        assert feed.source == FeedSource.LA_RAZON
        assert feed.url.value is not None
        url = urlsplit(feed.url.value)
        assert url.scheme in ("http", "https")
        assert url.hostname is not None
        assert url.hostname.endswith("larazon.es")
        assert isinstance(feed.category, FeedCategory)
        assert feed.author.value
        assert feed.title.value
        assert feed.description.value != ""
