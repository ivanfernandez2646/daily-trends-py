import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

pytestmark = pytest.mark.integration

scenarios("features/update-feed.feature")


def create_feed(client: TestClient) -> dict[str, object]:
    id = MotherCreator.uuid()
    response = client.put(
        f"/feed/{id}", json={"title": "A title", "description": "A description", "author": "Ivan"}
    )
    assert response.status_code == 201
    return response.json()


def test_an_empty_body_answers_the_unchanged_feed(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={})

    assert response.status_code == 200
    assert response.json() == feed


def test_a_null_description_is_stored_with_a_new_update_date(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"description": None})

    assert response.status_code == 200
    body = response.json()
    assert body == {**feed, "description": None, "updatedAt": body["updatedAt"]}
    assert body["updatedAt"] is not None
    assert client.get(f"/feed/{feed['id']}").json() == body


def test_a_blank_title_answers_400(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"title": "  "})

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedTitle> is mandatory. Current value: <  >"}


def test_rejects_an_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.patch("/feed/not-a-uuid", json={"title": "A title"})

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}
