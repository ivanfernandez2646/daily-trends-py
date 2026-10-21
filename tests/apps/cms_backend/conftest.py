import json
from collections.abc import Awaitable, Callable, Iterator
from typing import cast

import httpx2
import pytest
from dishka import AsyncContainer
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, then, when

from daily_trends_py.apps.cms_backend.container import create_container
from daily_trends_py.apps.cms_backend.main import create_app
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
)
from daily_trends_py.contexts.cms.users.domain.access_token_issuer import AccessTokenIssuer
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother
from tests.contexts.cms.users.domain.user_id_mother import UserIdMother
from tests.mongo import TEST_MONGO_URL
from tests.scrape_fixtures import FrontPagesTransport


def run_in_app[T](client: TestClient, function: Callable[[], Awaitable[T]]) -> T:
    """Run a coroutine on the app's event loop, where its Mongo client lives."""
    assert client.portal is not None, "the client must be started with `with`"
    return client.portal.call(function)


@pytest.fixture
def front_pages_transport() -> FrontPagesTransport:
    return FrontPagesTransport()


@pytest.fixture
def settings() -> Settings:
    return IsolatedSettings(mongo_url=TEST_MONGO_URL)


@pytest.fixture
def container(settings: Settings, front_pages_transport: FrontPagesTransport) -> AsyncContainer:
    # The app's lifespan closes it.
    return create_container(settings, http_transport=front_pages_transport)


@pytest.fixture
def app(container: AsyncContainer) -> FastAPI:
    return create_app(container)


@pytest.fixture
def raise_server_exceptions() -> bool:
    """Whether the client re-raises an error the app answered with a 500; override to test 500s."""
    return True


@pytest.fixture
def client(
    app: FastAPI, container: AsyncContainer, raise_server_exceptions: bool
) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=raise_server_exceptions) as test_client:
        database = resolve_mongo_client(test_client, container).get_default_database()
        for collection in (database["feeds"], database["users"]):
            run_in_app(test_client, lambda collection=collection: collection.delete_many({}))
        authenticate(test_client, container)
        yield test_client


@pytest.fixture
def anonymous_client(client: TestClient) -> TestClient:
    """The same client, without the access token it sends by default."""
    del client.headers["Authorization"]
    return client


def access_token_for(client: TestClient, container: AsyncContainer) -> str:
    """A valid access token for some user: verifying one never reads the stored users."""
    issuer = resolve(client, container, AccessTokenIssuer)
    return issuer.issue(UserIdMother.random()).value


def authenticate(client: TestClient, container: AsyncContainer) -> None:
    """Send a valid access token with every request, as an administrator would."""
    client.headers["Authorization"] = f"Bearer {access_token_for(client, container)}"


def resolve[T](client: TestClient, container: AsyncContainer, dependency: type[T]) -> T:
    """The app's instance of `dependency`, resolved on the app's event loop."""
    return run_in_app(client, lambda: container.get(dependency))


def resolve_mongo_client(client: TestClient, container: AsyncContainer) -> MongoClient:
    # `MongoClient` is a type alias, which `resolve` cannot take as `type[T]`.
    mongo_client: MongoClient = run_in_app(client, lambda: container.get(MongoClient))
    return mongo_client


@given("There are feeds:")
def there_are_feeds(
    container: AsyncContainer, client: TestClient, datatable: list[list[str]]
) -> None:
    header, *rows = datatable
    repository = resolve(client, container, FeedRepository)
    for row in rows:
        values = dict(zip(header, row, strict=True))
        created_at = values.get("createdAt")
        feed = FeedMother.from_primitives(
            {
                "id": values["id"],
                "title": values["title"],
                "description": values["description"],
                "author": values["author"],
                "source": FeedSource(values["source"]),
                "category": FeedCategory(values["category"]),
                "url": values.get("url") or None,
                "created_at": (
                    FeedCreatedAtMother.create(created_at)
                    if created_at
                    else FeedCreatedAtMother.now()
                ).value,
                "updated_at": FeedUpdatedAtMother.random().value,
            }
        )
        run_in_app(client, lambda feed=feed: repository.create(feed))


@when(parsers.parse('I send a GET request to "{path}"'), target_fixture="response")
def send_get_request(client: TestClient, path: str) -> httpx2.Response:
    return client.get(path)


@when(parsers.parse('I send a PUT request to "{path}" with body:'), target_fixture="response")
def send_put_request_with_body(client: TestClient, path: str, docstring: str) -> httpx2.Response:
    return client.put(path, json=json.loads(docstring))


@when(parsers.parse('I send a PATCH request to "{path}" with body:'), target_fixture="response")
def send_patch_request_with_body(client: TestClient, path: str, docstring: str) -> httpx2.Response:
    return client.patch(path, json=json.loads(docstring))


@when(parsers.parse('I send a DELETE request to "{path}"'), target_fixture="response")
def send_delete_request(client: TestClient, path: str) -> httpx2.Response:
    return client.delete(path)


@then(parsers.parse("The response status code should be {status_code:d}"))
def response_status_code_is(response: httpx2.Response, status_code: int) -> None:
    assert response.status_code == status_code


@then("The response should be:")
def response_is(response: httpx2.Response, docstring: str) -> None:
    assert response.json() == json.loads(docstring)


@then("The response should be empty")
def response_is_empty(response: httpx2.Response) -> None:
    assert response.content == b""


@then(parsers.parse("The response is an array with length {length:d}"))
def response_is_an_array_with_length(response: httpx2.Response, length: int) -> None:
    body: object = response.json()
    assert isinstance(body, list)
    assert len(cast(list[object], body)) == length


def _matching_part(actual: object, expected: object) -> object:
    """The part of `actual` shaped like `expected`: only its keys, at any depth, in list order."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        expected_fields = cast(dict[str, object], expected)
        actual_fields = cast(dict[str, object], actual)
        return {
            key: _matching_part(actual_fields.get(key), value)
            for key, value in expected_fields.items()
        }
    if isinstance(expected, list) and isinstance(actual, list):
        expected_items = cast(list[object], expected)
        actual_items = cast(list[object], actual)
        if len(actual_items) != len(expected_items):
            return actual_items
        return [
            _matching_part(item, value)
            for item, value in zip(actual_items, expected_items, strict=True)
        ]
    return actual


@then("The response should contains:")
def response_contains(response: httpx2.Response, docstring: str) -> None:
    expected: object = json.loads(docstring)
    assert _matching_part(response.json(), expected) == expected
