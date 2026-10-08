import pytest
from fastapi.testclient import TestClient

from tests.contexts.cms.shared.domain.mother_creator import MotherCreator
from tests.scrap_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration


def test_scraping_stores_the_front_page_feeds_next_to_the_existing_ones(
    client: TestClient,
) -> None:
    for title in ("First", "Second"):
        client.put(f"/feed/{MotherCreator.uuid()}", json={"title": title, "author": "Ivan"})

    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert response.content == b""
    assert len(client.get("/feed/list").json()) == 7


@pytest.mark.parametrize(
    "front_pages_transport", [FrontPagesTransport(failing_hosts={"www.elespanol.com"})]
)
def test_scraping_answers_ok_and_stores_nothing_when_the_source_fails(
    client: TestClient,
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert response.content == b""
    assert client.get("/feed/list").json() == []
