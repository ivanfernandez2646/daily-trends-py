from collections import Counter
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
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


async def test_scrapes_six_feeds_from_the_front_page(client: httpx.AsyncClient) -> None:
    feeds = await ElConfidencialFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.author.value, feed.title.value) for feed in feeds] == [
        ("Marcos Ejemplo. Barcelona", "El ayuntamiento de Villaejemplo aprueba sus presupuestos"),
        ("Í. Prueba / J. Muestra", '"Abriremos el mercado los domingos", anuncia el alcalde'),
        ("Ramón Ficticio", "La biblioteca amplía su horario en verano"),
        ("Lucía Muestra", "El club de ajedrez gana el torneo regional"),
        ("Óscar Inventado", "Los vecinos estrenan un huerto urbano"),
        ("Nadie", "Una noticia sin sección también se guarda"),
    ]
    assert [feed.description.value for feed in feeds] == [
        "El pleno saca adelante las cuentas con el apoyo de la oposición.",
        None,
        None,
        None,
        None,
        None,
    ]
    assert {feed.source for feed in feeds} == {FeedSource.EL_CONFIDENCIAL}
    _assert_each_feed_was_created_once_now(feeds)


async def test_credits_each_feed_with_its_article_url_and_section_category(
    client: httpx.AsyncClient,
) -> None:
    feeds = await ElConfidencialFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.url.value, feed.category) for feed in feeds] == [
        (
            "https://www.elconfidencial.com/espana/2026-10-20/pleno-presupuestos_100001/",
            FeedCategory.POLITICS,
        ),
        (
            "https://www.elconfidencial.com/empresas/2026-10-20/mercado-domingos_100003/",
            FeedCategory.ECONOMY,
        ),
        (
            "https://www.elconfidencial.com/cultura/2026-10-20/biblioteca-verano_100005/",
            FeedCategory.CULTURE,
        ),
        (
            "https://www.elconfidencial.com/deportes/2026-10-20/ajedrez-torneo_100006/",
            FeedCategory.SPORTS,
        ),
        (
            "https://www.elconfidencial.com/motor/2026-10-20/huerto-urbano_100007/",
            FeedCategory.OTHER,
        ),
        ("https://www.elconfidencial.com/noticia-8.html", FeedCategory.OTHER),
    ]


@pytest.mark.parametrize(
    ("section", "category"),
    [
        ("espana", FeedCategory.POLITICS),
        ("mundo", FeedCategory.INTERNATIONAL),
        ("mercados", FeedCategory.ECONOMY),
        ("vivienda", FeedCategory.ECONOMY),
        ("inmobiliario", FeedCategory.ECONOMY),
        ("sociedad", FeedCategory.SOCIETY),
        ("television", FeedCategory.CULTURE),
        ("tecnologia", FeedCategory.TECHNOLOGY),
        ("salud", FeedCategory.HEALTH),
        ("opinion", FeedCategory.OPINION),
        ("juridico", FeedCategory.OTHER),
        ("motor", FeedCategory.OTHER),
    ],
)
async def test_maps_its_sections_to_categories(section: str, category: FeedCategory) -> None:
    page = (
        "<article><a class='teaser__link' href='{href}'>"
        "<h2 class='titleArticleEditable'>A title</h2></a>"
        "<span class='articleByline__signature'>Ana</span></article>"
    ).format(href=f"/{section}/1.html")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=page))
    async with httpx.AsyncClient(transport=transport) as client:
        [feed] = await ElConfidencialFeedScraper(client, FixedClock(NOW)).scrape()

    assert feed.category == category


@pytest.mark.network
async def test_scrapes_a_varied_selection_from_the_real_front_page() -> None:
    # The site answers 403 to httpx's default User-Agent, so the test sends the app's.
    async with httpx.AsyncClient(
        timeout=None, follow_redirects=True, headers={"User-Agent": "daily-trends-py"}
    ) as client:
        feeds = await ElConfidencialFeedScraper(client, FixedClock(NOW)).scrape()

    assert 1 <= len(feeds) <= 15
    assert max(Counter(feed.category for feed in feeds).values()) <= 2
    for feed in feeds:
        assert feed.source == FeedSource.EL_CONFIDENCIAL
        assert feed.url.value is not None
        url = urlsplit(feed.url.value)
        assert url.scheme in ("http", "https")
        assert url.hostname is not None
        assert url.hostname.endswith("elconfidencial.com")
        assert isinstance(feed.category, FeedCategory)
        assert feed.author.value
        assert feed.title.value
        assert feed.description.value != ""
