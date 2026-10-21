import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

pytestmark = pytest.mark.integration

scenarios("features/update-feed.feature")


def create_feed(client: TestClient) -> dict[str, object]:
    id = MotherCreator.uuid()
    response = client.put(
        f"/feed/{id}",
        json={
            "title": "A title",
            "description": "A description",
            "author": "Ivan",
            "category": "OTHER",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_an_empty_body_answers_the_unchanged_feed(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={})

    assert response.status_code == 200
    assert response.json() == feed


def test_no_body_answers_the_unchanged_feed(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}")

    assert response.status_code == 200
    assert response.json() == feed


def test_a_null_description_is_stored_with_a_new_update_date(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"description": None})

    assert response.status_code == 200
    body = response.json()
    assert body == {**feed, "description": None, "updated_at": body["updated_at"]}
    assert body["updated_at"] is not None
    assert client.get(f"/feed/{feed['id']}").json() == body


@pytest.mark.parametrize("title", ["  ", ""])
def test_a_blank_title_answers_400_and_keeps_the_feed(client: TestClient, title: str) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"title": title})

    assert response.status_code == 400
    assert response.json() == {"error": f"<FeedTitle> is mandatory. Current value: <{title}>"}
    assert client.get(f"/feed/{feed['id']}").json() == feed


@pytest.mark.parametrize("title", [None, 0])
def test_a_title_that_is_not_a_string_answers_400_and_keeps_the_feed(
    client: TestClient, title: object
) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"title": title})

    assert response.status_code == 400
    assert response.json() == {"error": "title: Input should be a valid string"}
    assert client.get(f"/feed/{feed['id']}").json() == feed


def test_the_body_is_validated_before_the_feed_is_looked_up(client: TestClient) -> None:
    response = client.patch(f"/feed/{MotherCreator.uuid()}", json={"title": 0})

    assert response.status_code == 400
    assert response.json() == {"error": "title: Input should be a valid string"}


def test_an_empty_title_on_a_missing_feed_answers_404(client: TestClient) -> None:
    id = MotherCreator.uuid()

    response = client.patch(f"/feed/{id}", json={"title": ""})

    assert response.status_code == 404
    assert response.json() == {"error": f"Feed with id <{id}> not found"}


def test_rejects_an_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.patch("/feed/not-a-uuid", json={"title": "A title"})

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}


def test_a_new_category_is_stored_with_a_new_update_date(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"category": "SPORTS"})

    assert response.status_code == 200
    body = response.json()
    assert body | {"updated_at": None} == feed | {"category": "SPORTS"}
    assert body["updated_at"] is not None
    assert client.get(f"/feed/{feed['id']}").json() == body


def test_the_same_category_answers_the_unchanged_feed(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"category": "OTHER"})

    assert response.status_code == 200
    assert response.json() == feed


@pytest.mark.parametrize(
    "category",
    [
        pytest.param(None, id="null"),
        pytest.param("sports", id="lowercase"),
        pytest.param(1, id="number"),
    ],
)
def test_a_category_that_is_not_a_known_value_answers_400_and_keeps_the_feed(
    client: TestClient, category: object
) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"category": category})

    assert response.status_code == 400
    assert str(response.json()["error"]).startswith("category: ")
    assert client.get(f"/feed/{feed['id']}").json() == feed


def test_the_url_cannot_be_changed(client: TestClient) -> None:
    feed = create_feed(client)

    response = client.patch(f"/feed/{feed['id']}", json={"url": "https://www.elmundo.es/1.html"})

    assert response.status_code == 200
    assert response.json() == feed
