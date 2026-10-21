from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

pytestmark = pytest.mark.integration

scenarios("features/create-feed.feature")

REQUIRED_FIELDS = "title: Field required; author: Field required; category: Field required"
UNKNOWN_CATEGORY = (
    "category: Input should be 'POLITICS', 'INTERNATIONAL', 'ECONOMY', 'SOCIETY', 'SPORTS',"
    " 'CULTURE', 'TECHNOLOGY', 'SCIENCE', 'HEALTH', 'OPINION' or 'OTHER'"
)
NOT_A_JSON_OBJECT = "body: Input should be a valid dictionary or object to extract fields from"


def test_creating_the_same_id_twice_answers_409_and_keeps_the_first_feed(
    client: TestClient,
) -> None:
    id = MotherCreator.uuid()
    created = client.put(
        f"/feed/{id}", json={"title": "First", "author": "Ivan", "category": "OTHER"}
    )

    response = client.put(
        f"/feed/{id}", json={"title": "Second", "author": "Ivan", "category": "OTHER"}
    )

    assert created.status_code == 201
    assert response.status_code == 409
    assert "location" not in response.headers
    assert response.json() == {"error": f"Feed with id <{id}> already exists"}
    assert client.get(f"/feed/{id}").json() == created.json()


def test_two_concurrent_creations_of_the_same_id_answer_one_201_and_one_409(
    client: TestClient,
) -> None:
    id = MotherCreator.uuid()
    bodies = [
        {"title": "First", "author": "Ivan", "category": "OTHER"},
        {"title": "Second", "author": "Ivan", "category": "OTHER"},
    ]
    both_ready = Barrier(len(bodies))

    def put(body: dict[str, str]) -> httpx2.Response:
        both_ready.wait()
        return client.put(f"/feed/{id}", json=body)

    with ThreadPoolExecutor(max_workers=len(bodies)) as executor:
        responses = list(executor.map(put, bodies))

    assert sorted(response.status_code for response in responses) == [201, 409]
    [created] = [response for response in responses if response.status_code == 201]
    assert client.get(f"/feed/{id}").json() == created.json()


def test_creates_a_cms_feed_with_null_description_url_and_update_date(client: TestClient) -> None:
    id = MotherCreator.uuid()

    response = client.put(
        f"/feed/{id}",
        json={
            "title": "A title",
            "author": "Ivan",
            "category": "SPORTS",
            "source": "EL_PAIS",
            "url": "https://www.elmundo.es/deportes/1.html",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body | {"created_at": None} == {
        "id": id,
        "title": "A title",
        "description": None,
        "author": "Ivan",
        "source": "CMS",
        "category": "SPORTS",
        "url": None,
        "created_at": None,
        "updated_at": None,
    }
    assert client.get(f"/feed/{id}").json() == body


def test_rejects_an_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.put(
        "/feed/not-a-uuid", json={"title": "A title", "author": "Ivan", "category": "OTHER"}
    )

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}


def test_rejects_a_blank_title(client: TestClient) -> None:
    response = client.put(
        f"/feed/{MotherCreator.uuid()}", json={"title": "  ", "author": "Ivan", "category": "OTHER"}
    )

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedTitle> is mandatory. Current value: <  >"}


def _without_body(client: TestClient, url: str) -> httpx2.Response:
    return client.put(url)


def _with_an_empty_json_body(client: TestClient, url: str) -> httpx2.Response:
    return client.put(url, content="", headers={"content-type": "application/json"})


def _with_an_empty_object(client: TestClient, url: str) -> httpx2.Response:
    return client.put(url, json={})


@pytest.mark.parametrize("send", [_without_body, _with_an_empty_json_body, _with_an_empty_object])
def test_without_title_author_and_category_lists_them_as_required(
    client: TestClient, send: Callable[[TestClient, str], httpx2.Response]
) -> None:
    response = send(client, f"/feed/{MotherCreator.uuid()}")

    assert response.status_code == 400
    assert response.json() == {"error": REQUIRED_FIELDS}


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            {"title": 0, "author": "Ivan", "category": "OTHER"},
            "title: Input should be a valid string",
        ),
        (
            {"title": None, "author": "Ivan", "category": "OTHER"},
            "title: Input should be a valid string",
        ),
        (
            {"title": "A title", "author": "Ivan", "category": "OTHER", "description": True},
            "description: Input should be a valid string",
        ),
        ({"title": "A title", "author": "Ivan"}, "category: Field required"),
        ({"title": "A title", "author": "Ivan", "category": None}, UNKNOWN_CATEGORY),
        ({"title": "A title", "author": "Ivan", "category": "WEATHER"}, UNKNOWN_CATEGORY),
        ({"title": "A title", "author": "Ivan", "category": "sports"}, UNKNOWN_CATEGORY),
        (["a title"], NOT_A_JSON_OBJECT),
        ("a title", NOT_A_JSON_OBJECT),
    ],
)
def test_rejects_values_that_are_not_strings_or_a_body_that_is_not_an_object(
    client: TestClient, body: object, message: str
) -> None:
    response = client.put(f"/feed/{MotherCreator.uuid()}", json=body)

    assert response.status_code == 400
    assert response.json() == {"error": message}


def test_rejects_an_urlencoded_body(client: TestClient) -> None:
    response = client.put(
        f"/feed/{MotherCreator.uuid()}",
        data={"title": "A title", "author": "Ivan", "category": "OTHER"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "body: Content type should be application/json"}


def test_rejects_malformed_json_as_json(client: TestClient) -> None:
    response = client.put(
        f"/feed/{MotherCreator.uuid()}",
        content='{"title": ',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "body: JSON decode error"}


def test_ignores_unknown_fields_and_the_url(client: TestClient) -> None:
    response = client.put(
        f"/feed/{MotherCreator.uuid()}",
        json={
            "title": "A title",
            "author": "Ivan",
            "category": "OTHER",
            "source": "EL_PAIS",
            "url": "https://www.elmundo.es/1.html",
            "extra": 1,
        },
    )

    assert response.status_code == 201
    assert (response.json()["source"], response.json()["url"]) == ("CMS", None)
