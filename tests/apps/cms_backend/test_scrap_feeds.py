import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.scrap_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/scrap-feed.feature")


@pytest.mark.parametrize(
    "front_pages_transport", [FrontPagesTransport(failing_hosts={"elmundo.es"})]
)
def test_scraping_stores_and_returns_the_other_source_when_one_fails(client: TestClient) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    scraped = response.json()
    assert [feed["source"] for feed in scraped] == ["EL_ESPANOL"] * 5
    stored = client.get("/feed/list").json()
    assert sorted(feed["id"] for feed in stored) == sorted(feed["id"] for feed in scraped)


@pytest.mark.parametrize(
    "front_pages_transport",
    [FrontPagesTransport(failing_hosts={"elmundo.es", "www.elespanol.com"})],
)
def test_scraping_answers_an_empty_array_and_stores_nothing_when_every_source_fails(
    client: TestClient,
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert response.json() == []
    assert client.get("/feed/list").json() == []


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
def test_scraping_returns_the_other_source_when_one_times_out(client: TestClient) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert [feed["source"] for feed in response.json()] == ["EL_ESPANOL"] * 5
