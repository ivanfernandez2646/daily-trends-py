from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.container import create_container
from daily_trends_py.apps.cms_backend.main import create_app
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from tests.apps.cms_backend.conftest import authenticate
from tests.apps.cms_backend.fakes_provider import FakesProvider
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.contexts.cms.feeds.domain.feed_description_mother import FeedDescriptionMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.mongo import TEST_MONGO_URL

pytestmark = pytest.mark.integration


@pytest.fixture
def existing_feed() -> Feed:
    return FeedMother.random(description=FeedDescriptionMother.create("A description"))


@pytest.fixture
def repository(existing_feed: Feed) -> InMemoryFeedRepository:
    return InMemoryFeedRepository([existing_feed])


@pytest.fixture
def client(repository: InMemoryFeedRepository) -> Iterator[TestClient]:
    # The feeds live in the fakes; Mongo is only reached at startup, to check it and migrate.
    container = create_container(
        IsolatedSettings(mongo_url=TEST_MONGO_URL), FakesProvider(repository=repository)
    )
    with TestClient(create_app(container)) as test_client:
        authenticate(test_client, container)
        yield test_client


def test_finds_a_feed_from_the_injected_repository(client: TestClient, existing_feed: Feed) -> None:
    response = client.get(f"/feed/{existing_feed.id.value}")

    assert response.status_code == 200
    assert response.json()["id"] == existing_feed.id.value


def test_patching_nothing_writes_nothing(
    client: TestClient, repository: InMemoryFeedRepository, existing_feed: Feed
) -> None:
    response = client.patch(f"/feed/{existing_feed.id.value}", json={})

    assert response.status_code == 200
    assert repository.updated == []


def test_patching_a_null_description_clears_only_the_description(
    client: TestClient, repository: InMemoryFeedRepository, existing_feed: Feed
) -> None:
    response = client.patch(f"/feed/{existing_feed.id.value}", json={"description": None})

    assert response.status_code == 200
    [updated] = repository.updated
    assert updated.description.value is None
    assert updated.title == existing_feed.title
    assert updated.author == existing_feed.author


@pytest.mark.parametrize(
    ("method", "body"),
    [
        pytest.param("GET", None, id="find"),
        pytest.param("DELETE", None, id="delete"),
        pytest.param("PATCH", {"title": "A title"}, id="update"),
    ],
)
def test_a_missing_feed_answers_404(
    client: TestClient, method: str, body: dict[str, str] | None
) -> None:
    missing_id = FeedIdMother.random().value

    response = client.request(method, f"/feed/{missing_id}", json=body)

    assert response.status_code == 404
    assert response.json() == {"error": f"Feed with id <{missing_id}> not found"}


def test_creating_an_existing_feed_answers_409(client: TestClient, existing_feed: Feed) -> None:
    id = existing_feed.id.value

    response = client.put(
        f"/feed/{id}", json={"title": "A title", "author": "Ivan", "category": "OTHER"}
    )

    assert response.status_code == 409
    assert response.json() == {"error": f"Feed with id <{id}> already exists"}


@pytest.mark.parametrize("method", ["GET", "DELETE", "PATCH", "PUT"])
def test_an_id_that_is_not_a_uuid_answers_400(client: TestClient, method: str) -> None:
    response = client.request(
        method, "/feed/not-a-uuid", json={"title": "A title", "author": "Ivan", "category": "OTHER"}
    )

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}
