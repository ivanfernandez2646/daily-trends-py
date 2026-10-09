from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from tests.apps.cms_backend.conftest import run_in_app
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.scrap_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/home-feed.feature")


def _feed_created_at(created_at: datetime, source: FeedSource) -> Feed:
    return FeedMother.random(
        source=source,
        created_at=FeedCreatedAtMother.create(
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


def _wait_for_the_background_scraping(app: FastAPI, client: TestClient) -> None:
    refresher: FeedHomeRefresher = app.state.feed_home_refresher
    run_in_app(client, refresher.join)


def test_home_answers_the_stale_feeds_and_shows_the_scraped_ones_after_the_background_run(
    app: FastAPI, client: TestClient
) -> None:
    stale = _save_stale_feed(app, client)

    stale_response = client.get("/feed/home")
    _wait_for_the_background_scraping(app, client)
    fresh_response = client.get("/feed/home")

    assert stale_response.status_code == 200
    assert [feed["id"] for feed in stale_response.json()] == [stale.id.value]
    assert len(client.get("/feed/list").json()) == 11
    assert fresh_response.status_code == 200
    fresh_ids = [feed["id"] for feed in fresh_response.json()]
    assert len(fresh_ids) == 10
    assert stale.id.value not in fresh_ids


@pytest.mark.parametrize(
    "front_pages_transport",
    [FrontPagesTransport(failing_hosts={"elmundo.es", "www.elespanol.com"})],
)
def test_home_returns_the_stale_feeds_when_every_source_fails(
    app: FastAPI, client: TestClient
) -> None:
    stale = _save_stale_feed(app, client)

    client.get("/feed/home")
    _wait_for_the_background_scraping(app, client)
    response = client.get("/feed/home")

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [stale.id.value]
