from collections import Counter
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
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


async def test_scrapes_six_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await LaVanguardiaFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("Eusebio Ejemplo | París", "Villaejemplo estrena un festival de cine al aire libre"),
        ("Í. Prueba", '"Plantaremos mil árboles este invierno", promete el alcalde'),
        ("Ramón Ficticio", "El equipo de baloncesto asciende de categoría"),
        ("Lucía Muestra", "Abre la primera librería del barrio"),
        ("Óscar Inventado", "La piscina municipal amplía su temporada"),
        ("Nadie", "Una noticia sin sección también se guarda"),
    ]
    assert [feed.description.value for feed in feeds] == [
        "Las proyecciones serán gratuitas durante todo agosto.",
        None,
        None,
        None,
        None,
        None,
    ]
    assert {feed.source for feed in feeds} == {FeedSource.LA_VANGUARDIA}
    _assert_each_feed_was_created_once_now(feeds)


async def test_credits_each_feed_with_its_article_url_and_section_category(
    client: httpx.AsyncClient,
) -> None:
    feeds = await LaVanguardiaFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.url.value, feed.category) for feed in feeds] == [
        (
            "https://www.lavanguardia.com/cultura/20261020/1000001/cine-verano.html",
            FeedCategory.CULTURE,
        ),
        (
            "https://www.lavanguardia.com/local/valencia/20261020/1000003/arboles-invierno.html",
            FeedCategory.SOCIETY,
        ),
        (
            "https://www.lavanguardia.com/deportes/20261020/1000005/baloncesto-ascenso.html",
            FeedCategory.SPORTS,
        ),
        (
            "https://www.lavanguardia.com/lacontra/20261020/1000006/libreria-barrio.html",
            FeedCategory.OTHER,
        ),
        (
            "https://www.lavanguardia.com/vida/20261020/1000007/piscina-temporada.html",
            FeedCategory.SOCIETY,
        ),
        ("https://www.lavanguardia.com/noticia-8.html", FeedCategory.OTHER),
    ]


@pytest.mark.parametrize(
    ("section", "category"),
    [
        ("politica", FeedCategory.POLITICS),
        ("internacional", FeedCategory.INTERNATIONAL),
        ("dinero", FeedCategory.ECONOMY),
        ("local", FeedCategory.SOCIETY),
        ("television", FeedCategory.CULTURE),
        ("tecnologia", FeedCategory.TECHNOLOGY),
        ("ciencia", FeedCategory.SCIENCE),
        ("salud", FeedCategory.HEALTH),
        ("opinion", FeedCategory.OPINION),
        ("comer", FeedCategory.OTHER),
        ("historiayvida", FeedCategory.OTHER),
    ],
)
async def test_maps_its_sections_to_categories(section: str, category: FeedCategory) -> None:
    page = (
        "<article><h2 class='title'><a href='{href}'>A title</a></h2>"
        "<div class='author-name'>Ana</div></article>"
    ).format(href=f"/{section}/1.html")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=page))
    async with httpx.AsyncClient(transport=transport) as client:
        [feed] = await LaVanguardiaFeedScraper(client, FixedClock(NOW)).scrape()

    assert feed.category == category


@pytest.mark.network
async def test_scrapes_a_varied_selection_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await LaVanguardiaFeedScraper(client, FixedClock(NOW)).scrape()

    assert 1 <= len(feeds) <= 15
    assert max(Counter(feed.category for feed in feeds).values()) <= 2
    for feed in feeds:
        assert feed.source == FeedSource.LA_VANGUARDIA
        assert feed.url.value is not None
        url = urlsplit(feed.url.value)
        assert url.scheme in ("http", "https")
        assert url.hostname is not None
        assert url.hostname.endswith("lavanguardia.com")
        assert isinstance(feed.category, FeedCategory)
        assert feed.author.value
        assert feed.title.value
        assert feed.description.value != ""
