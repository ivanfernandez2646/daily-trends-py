import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.scrap_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/scrap-feed.feature")


@pytest.mark.parametrize(
    "front_pages_transport", [FrontPagesTransport(failing_hosts={"elmundo.es"})]
)
def test_scraping_stores_the_other_source_when_one_fails(client: TestClient) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    feeds = client.get("/feed/list").json()
    assert [feed["source"] for feed in feeds] == ["EL_ESPANOL"] * 5


@pytest.mark.parametrize(
    "front_pages_transport",
    [FrontPagesTransport(failing_hosts={"elmundo.es", "www.elespanol.com"})],
)
def test_scraping_answers_ok_and_stores_nothing_when_every_source_fails(
    client: TestClient,
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert response.content == b""
    assert client.get("/feed/list").json() == []
