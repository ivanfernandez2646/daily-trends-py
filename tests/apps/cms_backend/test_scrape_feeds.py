import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.scrape_fixtures import EVERY_FRONT_PAGE_HOST, FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/scrap-feed.feature")

OTHER_SOURCES_THAN_EL_MUNDO = ["EL_ESPANOL", "EL_CONFIDENCIAL", "LA_RAZON", "LA_VANGUARDIA"]


def _sources(feeds: list[dict[str, object]]) -> list[object]:
    return sorted({feed["source"] for feed in feeds}, key=str)


def test_scraping_reads_the_five_front_pages(
    client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert {request.url.host for request in front_pages_transport.requests} >= {
        "www.elmundo.es",
        "www.elespanol.com",
        "www.elconfidencial.com",
        "www.larazon.es",
        "www.lavanguardia.com",
    }
    scraped = response.json()
    assert len(scraped) == 31
    assert _sources(scraped) == sorted([*OTHER_SOURCES_THAN_EL_MUNDO, "EL_MUNDO"])


def test_scraped_feeds_keep_their_article_url_and_section_category(client: TestClient) -> None:
    scraped = client.get("/feed/scrap").json()

    assert all(str(feed["url"]).startswith("https://www.") for feed in scraped)
    [la_razon_sports] = [
        feed for feed in scraped if feed["url"] == "https://www.larazon.es/deportes/futbol/123.html"
    ]
    assert (la_razon_sports["source"], la_razon_sports["category"]) == ("LA_RAZON", "SPORTS")
    sports = client.get("/feed/list", params={"category": "SPORTS", "limit": 100}).json()["items"]
    assert la_razon_sports in sports
    assert {feed["source"] for feed in sports} == {
        "EL_MUNDO",
        "EL_CONFIDENCIAL",
        "LA_RAZON",
        "LA_VANGUARDIA",
    }


@pytest.mark.parametrize(
    "front_pages_transport", [FrontPagesTransport(failing_hosts={"elmundo.es"})]
)
def test_scraping_stores_and_returns_the_other_sources_when_one_fails(
    client: TestClient,
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    scraped = response.json()
    assert len(scraped) == 25
    assert _sources(scraped) == sorted(OTHER_SOURCES_THAN_EL_MUNDO)
    stored = client.get("/feed/list", params={"limit": 100}).json()["items"]
    assert sorted(feed["id"] for feed in stored) == sorted(feed["id"] for feed in scraped)


@pytest.mark.parametrize(
    "front_pages_transport",
    [FrontPagesTransport(failing_hosts=EVERY_FRONT_PAGE_HOST)],
)
def test_scraping_answers_an_empty_array_and_stores_nothing_when_every_source_fails(
    client: TestClient,
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert response.json() == []
    assert client.get("/feed/list").json()["items"] == []


def test_scraping_identifies_itself_with_a_user_agent(
    client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    client.get("/feed/scrap")

    assert front_pages_transport.requests
    assert {request.headers["User-Agent"] for request in front_pages_transport.requests} == {
        "daily-trends-py"
    }


@pytest.mark.parametrize(
    "front_pages_transport", [FrontPagesTransport(timing_out_hosts={"www.elmundo.es"})]
)
def test_scraping_returns_the_other_sources_when_one_times_out(client: TestClient) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    scraped = response.json()
    assert len(scraped) == 25
    assert _sources(scraped) == sorted(OTHER_SOURCES_THAN_EL_MUNDO)
