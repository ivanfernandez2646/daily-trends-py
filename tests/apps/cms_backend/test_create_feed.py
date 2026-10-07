import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

pytestmark = pytest.mark.integration

scenarios("features/create-feed.feature")


def test_creating_the_same_id_twice_answers_302_and_keeps_the_first_feed(
    client: TestClient,
) -> None:
    id = MotherCreator.uuid()
    created = client.put(f"/feed/{id}", json={"title": "First", "author": "Ivan"})

    response = client.put(f"/feed/{id}", json={"title": "Second", "author": "Ivan"})

    assert created.status_code == 201
    assert response.status_code == 302
    assert "location" not in response.headers
    assert response.json() == {"error": f"Feed with id <{id}> already exists"}
    assert client.get(f"/feed/{id}").json() == created.json()


def test_creates_a_cms_feed_with_null_description_and_update_date(client: TestClient) -> None:
    id = MotherCreator.uuid()

    response = client.put(
        f"/feed/{id}", json={"title": "A title", "author": "Ivan", "source": "EL_PAIS"}
    )

    assert response.status_code == 201
    body = response.json()
    assert list(body) == [
        "id",
        "title",
        "description",
        "author",
        "source",
        "createdAt",
        "updatedAt",
    ]
    assert body | {"createdAt": None} == {
        "id": id,
        "title": "A title",
        "description": None,
        "author": "Ivan",
        "source": "CMS",
        "createdAt": None,
        "updatedAt": None,
    }


def test_rejects_an_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.put("/feed/not-a-uuid", json={"title": "A title", "author": "Ivan"})

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}


def test_rejects_a_blank_title(client: TestClient) -> None:
    response = client.put(f"/feed/{MotherCreator.uuid()}", json={"title": "  ", "author": "Ivan"})

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedTitle> is mandatory. Current value: <  >"}
