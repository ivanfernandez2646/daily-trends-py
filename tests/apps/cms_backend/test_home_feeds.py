from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from tests.apps.cms_backend.conftest import run_in_app
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.shared.domain.date_time_value_object_mother import (
    RequiredDateTimeValueObjectMother,
)
from tests.scrap_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/home-feed.feature")


def _feed_created_at(created_at: datetime, source: FeedSource) -> Feed:
    return FeedMother.random(
        source=source,
        created_at=RequiredDateTimeValueObjectMother.create(
            created_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        ),
    )


def test_home_returns_the_ten_newest_external_feeds(app: FastAPI, client: TestClient) -> None:
    now = datetime.now(UTC)
    external_sources = [FeedSource.EL_MUNDO, FeedSource.EL_ESPANOL]
    external_feeds = [
        _feed_created_at(
            now - timedelta(milliseconds=index + 1), source=external_sources[index % 2]
        )
        for index in range(11)
    ]
    cms_feed = _feed_created_at(now, source=FeedSource.CMS)
    repository = MongoFeedRepository(app.state.mongo_client)
    for feed in [cms_feed, *reversed(external_feeds)]:
        run_in_app(client, lambda feed=feed: repository.save(feed))

    response = client.get("/feed/home")

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [
        feed.id.value for feed in external_feeds[:10]
    ]


def _save_stale_feed(app: FastAPI, client: TestClient) -> Feed:
    stale = _feed_created_at(datetime(2023, 6, 17, 14, 58, tzinfo=UTC), FeedSource.EL_MUNDO)
    repository = MongoFeedRepository(app.state.mongo_client)
    run_in_app(client, lambda: repository.save(stale))
    return stale


def test_home_scrapes_and_returns_the_new_feeds_when_the_newest_is_stale(
    app: FastAPI, client: TestClient
) -> None:
    stale = _save_stale_feed(app, client)

    response = client.get("/feed/home")

    assert response.status_code == 200
    feeds = response.json()
    assert len(feeds) == 10
    assert stale.id.value not in [feed["id"] for feed in feeds]
    assert len(client.get("/feed/list").json()) == 11


@pytest.mark.parametrize(
    "front_pages_transport",
    [FrontPagesTransport(failing_hosts={"elmundo.es", "www.elespanol.com"})],
)
def test_home_returns_the_stale_feeds_when_every_source_fails(
    app: FastAPI, client: TestClient
) -> None:
    stale = _save_stale_feed(app, client)

    response = client.get("/feed/home")

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [stale.id.value]
