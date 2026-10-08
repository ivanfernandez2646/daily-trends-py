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


@pytest.mark.parametrize(("title", "rendered"), [("  ", "  "), ("", ""), (None, "null")])
def test_a_blank_or_null_title_answers_400_and_keeps_the_feed(
    client: TestClient, title: str | None, rendered: str
) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"title": title})

    assert response.status_code == 400
    assert response.json() == {"error": f"<FeedTitle> is mandatory. Current value: <{rendered}>"}
    assert client.get(f"/feed/{feed['id']}").json() == feed


def test_an_empty_title_on_a_missing_feed_answers_404(client: TestClient) -> None:
    id = MotherCreator.uuid()

    response = client.patch(f"/feed/{id}", json={"title": ""})

    assert response.status_code == 404
    assert response.json() == {"error": f"Feed with id <{id}> not found"}


def test_rejects_an_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.patch("/feed/not-a-uuid", json={"title": "A title"})

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}
