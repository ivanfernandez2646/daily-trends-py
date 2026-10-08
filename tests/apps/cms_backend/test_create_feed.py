import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

pytestmark = pytest.mark.integration

scenarios("features/create-feed.feature")


def test_creating_the_same_id_twice_answers_409_and_keeps_the_first_feed(
    client: TestClient,
) -> None:
    id = MotherCreator.uuid()
    created = client.put(f"/feed/{id}", json={"title": "First", "author": "Ivan"})

    response = client.put(f"/feed/{id}", json={"title": "Second", "author": "Ivan"})

    assert created.status_code == 201
    assert response.status_code == 409
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


def test_without_body_the_title_is_undefined(client: TestClient) -> None:
    response = client.put(f"/feed/{MotherCreator.uuid()}")

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedTitle> is mandatory. Current value: <undefined>"}


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"title": None, "author": "Ivan"}, "<FeedTitle> is mandatory. Current value: <null>"),
        ({"title": 123, "author": "Ivan"}, "<FeedTitle> is mandatory. Current value: <123>"),
        (
            {"title": "A title", "author": "Ivan", "description": True},
            "<FeedDescription> does not allow the value <true>",
        ),
        (["a title"], "<FeedTitle> is mandatory. Current value: <undefined>"),
    ],
)
def test_rejects_null_non_string_or_non_object_values(
    client: TestClient, body: object, message: str
) -> None:
    response = client.put(f"/feed/{MotherCreator.uuid()}", json=body)

    assert response.status_code == 400
    assert response.json() == {"error": message}


def test_creates_a_feed_from_an_urlencoded_body(client: TestClient) -> None:
    id = MotherCreator.uuid()

    response = client.put(f"/feed/{id}", data={"title": "A title", "author": "Ivan"})

    assert response.status_code == 201
    assert response.json()["title"] == "A title"


def test_rejects_an_urlencoded_body_with_a_repeated_title(client: TestClient) -> None:
    response = client.put(
        f"/feed/{MotherCreator.uuid()}",
        content="title=a&title=b&author=Ivan",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedTitle> is mandatory. Current value: <a,b>"}


@pytest.mark.parametrize("content", ['{"title": ', '"a title"', "123"])
def test_rejects_malformed_or_non_object_json_with_a_plain_bad_request(
    client: TestClient, content: str
) -> None:
    response = client.put(
        f"/feed/{MotherCreator.uuid()}",
        content=content,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "Bad Request"
