import json
from collections.abc import Awaitable, Callable, Iterator
from typing import cast

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, then, when

from daily_trends_py.apps.cms_backend.main import create_app
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
)
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.shared.domain.date_time_value_object_mother import (
    DateTimeValueObjectMother,
    RequiredDateTimeValueObjectMother,
)
from tests.mongo import TEST_MONGO_URL
from tests.scrap_fixtures import FrontPagesTransport


def run_in_app[T](client: TestClient, function: Callable[[], Awaitable[T]]) -> T:
    """Run a coroutine on the app's event loop, where its Mongo client lives."""
    assert client.portal is not None, "the client must be started with `with`"
    return client.portal.call(function)


@pytest.fixture
def front_pages_transport() -> FrontPagesTransport:
    return FrontPagesTransport()


@pytest.fixture
def app(front_pages_transport: FrontPagesTransport) -> FastAPI:
    return create_app(Settings(mongo_url=TEST_MONGO_URL), http_transport=front_pages_transport)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        mongo_client: MongoClient = app.state.mongo_client
        feeds = mongo_client.get_default_database()["feeds"]
        run_in_app(test_client, lambda: feeds.delete_many({}))
        yield test_client


@given("There are feeds:")
def there_are_feeds(app: FastAPI, client: TestClient, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    repository = MongoFeedRepository(app.state.mongo_client)
    for row in rows:
        values = dict(zip(header, row, strict=True))
        feed = FeedMother.from_primitives(
            {
                "id": values["id"],
                "title": values["title"],
                "description": values["description"],
                "author": values["author"],
                "source": FeedSource(values["source"]),
                "createdAt": values.get("createdAt")
                or RequiredDateTimeValueObjectMother.random().value,
                "updatedAt": DateTimeValueObjectMother.random().value,
            }
        )
        run_in_app(client, lambda feed=feed: repository.save(feed))


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
