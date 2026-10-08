import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
)
from tests.apps.cms_backend.conftest import run_in_app
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother

pytestmark = pytest.mark.integration


@pytest.fixture
def malformed_feed_id(app: FastAPI, client: TestClient) -> str:
    """An external feed whose stored `createdAt` was written by something other than this API."""
    mongo_client: MongoClient = app.state.mongo_client
    feeds = mongo_client.get_default_database()["feeds"]
    primitives = FeedMother.random(source=FeedSource.EL_MUNDO).to_primitives()
    document = {**primitives, "_id": primitives["id"], "createdAt": "not-a-date"}
    del document["id"]
    run_in_app(client, lambda: feeds.insert_one(document))
    return primitives["id"]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/feed/{id}", None),
        ("PUT", "/feed/{id}", {"title": "A title", "author": "Ivan"}),
        ("PATCH", "/feed/{id}", {"title": "A title"}),
        ("DELETE", "/feed/{id}", None),
        ("GET", "/feed/list", None),
        ("GET", "/feed/home", None),
    ],
)
def test_an_invalid_stored_feed_answers_500(
    client: TestClient,
    malformed_feed_id: str,
    method: str,
    path: str,
    body: dict[str, str] | None,
) -> None:
    response = client.request(method, path.format(id=malformed_feed_id), json=body)

    assert response.status_code == 500
    assert response.json() == {
        "error": f"Stored feed <{malformed_feed_id}> is invalid: "
        "<FeedCreatedAt> does not allow the value <not-a-date>"
    }
