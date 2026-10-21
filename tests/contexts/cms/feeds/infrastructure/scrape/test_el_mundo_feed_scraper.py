from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
import pytest

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
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
        f"{kicker}</span><a class='ue-c-cover-content__link' href='/espana/1.html'>"
        "<h2 class='ue-c-cover-content__headline'>A title</h2></a>"
        "<span class='ue-c-cover-content__byline-name'>"
        "<a class='ue-c-cover-content__link'>Ana</a></span></article>"
    )
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=page))
    async with httpx.AsyncClient(transport=transport) as client:
        [feed] = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert feed.description.value == description
    _assert_each_feed_was_created_once_now([feed])


async def test_credits_each_feed_with_its_article_url_and_section_category(
    client: httpx.AsyncClient,
) -> None:
    feeds = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert [(feed.url.value, feed.category) for feed in feeds] == [
        ("https://www.elmundo.es/madrid/2026/10/20/mercado-productores.html", FeedCategory.SOCIETY),
        ("https://www.elmundo.es/deportes/2026/10/20/carrera-solidaria.html", FeedCategory.SPORTS),
        ("https://www.elmundo.es/cultura/2026/10/20/museo-juguetes.html", FeedCategory.CULTURE),
        ("https://www.elmundo.es/juegos/crucigrama/", FeedCategory.OTHER),
        (
            "https://www.elmundo.es/ciencia/2026/10/20/astronomia.html?utm=portada",
            FeedCategory.SCIENCE,
        ),
    ]


@pytest.mark.parametrize(
    ("section", "category"),
    [
        ("espana", FeedCategory.POLITICS),
        ("elecciones", FeedCategory.POLITICS),
        ("internacional", FeedCategory.INTERNATIONAL),
        ("economia", FeedCategory.ECONOMY),
        ("baleares", FeedCategory.SOCIETY),
        ("television", FeedCategory.CULTURE),
        ("tecnologia", FeedCategory.TECHNOLOGY),
        ("salud", FeedCategory.HEALTH),
        ("opinion", FeedCategory.OPINION),
        ("juegos", FeedCategory.OTHER),
        ("papel", FeedCategory.OTHER),
    ],
)
async def test_maps_its_sections_to_categories(section: str, category: FeedCategory) -> None:
    page = (
        "<article><a class='ue-c-cover-content__link' href='{href}'>"
        "<h2 class='ue-c-cover-content__headline'>A title</h2></a>"
        "<span class='ue-c-cover-content__byline-name'>"
        "<a class='ue-c-cover-content__link' href='/autor/ana.html'>Ana</a></span></article>"
    ).format(href=f"/{section}/1.html")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=page))
    async with httpx.AsyncClient(transport=transport) as client:
        [feed] = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert feed.category == category


@pytest.mark.network
async def test_scrapes_five_feeds_from_the_real_front_page() -> None:
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        feeds = await ElMundoFeedScraper(client, FixedClock(NOW)).scrape()

    assert len(feeds) == 5
    for feed in feeds:
        assert feed.source == FeedSource.EL_MUNDO
        assert feed.url.value is not None
        url = urlsplit(feed.url.value)
        assert url.scheme in ("http", "https")
        assert url.hostname is not None
        assert url.hostname.endswith("elmundo.es")
        assert isinstance(feed.category, FeedCategory)
        assert feed.author.value
        assert feed.title.value
        texts = (feed.author.value, feed.title.value, feed.description.value or "")
        assert not any(mojibake in text for text in texts for mojibake in ("Ã", "Â"))
