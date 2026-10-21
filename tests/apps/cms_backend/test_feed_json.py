import re

import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient

from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from tests.apps.cms_backend.conftest import resolve, run_in_app
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

pytestmark = pytest.mark.integration

FEED_KEYS = [
    "id",
    "title",
    "description",
    "author",
    "source",
    "category",
    "url",
    "created_at",
    "updated_at",
]
# Pydantic's format: UTC with `Z`, and six fractional digits only when the fraction is not zero.
UTC_DATE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3}000)?Z")


def _assert_is_feed_json(feed: dict[str, object]) -> None:
    assert list(feed) == FEED_KEYS
    assert isinstance(feed["created_at"], str)
    assert UTC_DATE.fullmatch(feed["created_at"])
    assert feed["updated_at"] is None or (
        isinstance(feed["updated_at"], str) and UTC_DATE.fullmatch(feed["updated_at"])
    )


def test_create_find_and_update_answer_the_feed_json(client: TestClient) -> None:
    url = f"/feed/{MotherCreator.uuid()}"

    created = client.put(url, json={"title": "A title", "author": "Ivan", "category": "OTHER"})
    found = client.get(url)
    updated = client.patch(url, json={"title": "Another title"})

    for response in (created, found, updated):
        assert response.is_success
        _assert_is_feed_json(response.json())
    assert isinstance(updated.json()["updated_at"], str)


def test_list_and_home_answer_feed_json(container: AsyncContainer, client: TestClient) -> None:
    feed = FeedMother.random(source=FeedSource.EL_MUNDO, created_at=FeedCreatedAtMother.now())
    repository = resolve(client, container, FeedRepository)
    run_in_app(client, lambda: repository.create(feed))

    for path in ("/feed/list", "/feed/home"):
        response = client.get(path)

        assert response.status_code == 200
        [listed] = response.json()
        _assert_is_feed_json(listed)


def test_scrape_answers_feed_json(client: TestClient) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    scraped = response.json()
    assert scraped
    for feed in scraped:
        _assert_is_feed_json(feed)
        assert isinstance(feed["url"], str)
        assert isinstance(feed["category"], str)
