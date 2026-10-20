from datetime import UTC, datetime, timedelta

import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from tests.apps.cms_backend.conftest import resolve, run_in_app
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.mongo import TEST_MONGO_URL
from tests.scrape_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/home-feed.feature")


def _feed_created_at(created_at: datetime, source: FeedSource) -> Feed:
    return FeedMother.random(
        source=source,
        created_at=FeedCreatedAtMother.create(created_at),
    )


def test_home_returns_the_ten_newest_external_feeds(
    container: AsyncContainer, client: TestClient
) -> None:
    now = datetime.now(UTC)
    external_sources = [FeedSource.EL_MUNDO, FeedSource.EL_ESPANOL]
    external_feeds = [
        _feed_created_at(
            now - timedelta(milliseconds=index + 1), source=external_sources[index % 2]
        )
        for index in range(11)
    ]
    cms_feed = _feed_created_at(now, source=FeedSource.CMS)
    repository = resolve(client, container, FeedRepository)
    for feed in [cms_feed, *reversed(external_feeds)]:
        run_in_app(client, lambda feed=feed: repository.create(feed))

    response = client.get("/feed/home")

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [
        feed.id.value for feed in external_feeds[:10]
    ]


def _save_stale_feed(container: AsyncContainer, client: TestClient) -> Feed:
    stale = _feed_created_at(datetime(2023, 6, 17, 14, 58, tzinfo=UTC), FeedSource.EL_MUNDO)
    repository = resolve(client, container, FeedRepository)
    run_in_app(client, lambda: repository.create(stale))
    return stale


def _wait_for_the_background_scraping(container: AsyncContainer, client: TestClient) -> None:
    refresher = resolve(client, container, FeedHomeRefresher)
    run_in_app(client, refresher.join)


def test_home_answers_the_stale_feeds_and_shows_the_scraped_ones_after_the_background_run(
    container: AsyncContainer, client: TestClient
) -> None:
    stale = _save_stale_feed(container, client)

    stale_response = client.get("/feed/home")
    _wait_for_the_background_scraping(container, client)
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
def test_home_keeps_the_stale_feeds_without_retrying_in_the_cooldown_when_every_source_fails(
    container: AsyncContainer, client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    stale = _save_stale_feed(container, client)
    client.get("/feed/home")
    _wait_for_the_background_scraping(container, client)
    requests_of_the_first_run = len(front_pages_transport.requests)

    response = client.get("/feed/home")
    _wait_for_the_background_scraping(container, client)

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [stale.id.value]
    assert requests_of_the_first_run > 0
    assert len(front_pages_transport.requests) == requests_of_the_first_run


@pytest.mark.parametrize(
    ("settings", "front_pages_transport"),
    [
        (
            IsolatedSettings(mongo_url=TEST_MONGO_URL, scrape_cooldown_seconds=0),
            FrontPagesTransport(failing_hosts={"elmundo.es", "www.elespanol.com"}),
        )
    ],
)
def test_home_retries_right_after_a_failed_run_when_the_cooldown_is_zero(
    container: AsyncContainer, client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    _save_stale_feed(container, client)
    client.get("/feed/home")
    _wait_for_the_background_scraping(container, client)
    requests_of_the_first_run = len(front_pages_transport.requests)

    client.get("/feed/home")
    _wait_for_the_background_scraping(container, client)

    assert requests_of_the_first_run > 0
    assert len(front_pages_transport.requests) == 2 * requests_of_the_first_run
