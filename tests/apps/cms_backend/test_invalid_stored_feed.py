import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient

from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from tests.apps.cms_backend.conftest import resolve_mongo_client, run_in_app
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.infrastructure.persistence.mongo.feed_document_mother import (
    MISSING,
    FeedDocumentMother,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def raise_server_exceptions() -> bool:
    return False


@pytest.fixture(
    params=[
        pytest.param(
            ({"createdAt": "not-a-date"}, "<FeedCreatedAt> does not allow the value <not-a-date>"),
            id="created at not a date",
        ),
        pytest.param(
            ({"title": MISSING}, "<FeedTitle> does not allow the value <None>"),
            id="missing title",
        ),
        pytest.param(
            ({"category": "WEATHER"}, "<FeedCategory> does not allow the value <WEATHER>"),
            id="unknown category",
        ),
    ]
)
def broken(request: pytest.FixtureRequest) -> tuple[dict[str, object], str]:
    """Stored fields written by something other than this API, and why the domain rejects them."""
    return request.param


@pytest.fixture
def malformed_feed_id(
    container: AsyncContainer, client: TestClient, broken: tuple[dict[str, object], str]
) -> str:
    mongo_client = resolve_mongo_client(client, container)
    feeds = mongo_client.get_default_database()["feeds"]
    overrides, _ = broken
    document = FeedDocumentMother.create(FeedMother.random(source=FeedSource.EL_MUNDO), **overrides)
    run_in_app(client, lambda: feeds.insert_one(document))
    return str(document["_id"])


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/feed/{id}", None),
        ("PATCH", "/feed/{id}", {"title": "A title"}),
        ("DELETE", "/feed/{id}", None),
        ("GET", "/feed/list", None),
        ("GET", "/feed/home", None),
    ],
)
def test_an_invalid_stored_feed_answers_a_generic_500_and_logs_why(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    malformed_feed_id: str,
    broken: tuple[dict[str, object], str],
    method: str,
    path: str,
    body: dict[str, str] | None,
) -> None:
    url = path.format(id=malformed_feed_id)

    response = client.request(method, url, json=body)

    assert response.status_code == 500
    assert response.json() == {"error": "Internal server error"}
    [record] = [record for record in caplog.records if record.exc_info]
    assert record.getMessage() == f"Unhandled error on {method} {url}"
    _, reason = broken
    assert f"Stored feed <{malformed_feed_id}> is invalid: {reason}" in caplog.text


def test_creating_over_an_invalid_stored_feed_answers_409(
    client: TestClient, malformed_feed_id: str
) -> None:
    response = client.put(
        f"/feed/{malformed_feed_id}",
        json={"title": "A title", "author": "Ivan", "category": "OTHER"},
    )

    assert response.status_code == 409
    assert response.json() == {"error": f"Feed with id <{malformed_feed_id}> already exists"}
