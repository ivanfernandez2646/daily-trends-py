import asyncio
from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from tests.apps.cms_backend.conftest import resolve, run_in_app
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.scrape_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/home-feed.feature")


def _feed_created_at(created_at: datetime, source: FeedSource) -> Feed:
    return FeedMother.random(
        source=source,
        created_at=FeedCreatedAtMother.create(created_at),
    )


def test_home_returns_the_two_newest_feeds_of_each_external_source(
    container: AsyncContainer, client: TestClient
) -> None:
    now = datetime.now(UTC)
    external_sources = [
        FeedSource.EL_MUNDO,
        FeedSource.EL_ESPANOL,
        FeedSource.EL_CONFIDENCIAL,
        FeedSource.LA_RAZON,
        FeedSource.LA_VANGUARDIA,
    ]
    external_feeds = [
        [
            _feed_created_at(now - timedelta(minutes=10 * index + age), source=source)
            for age in range(1, 4)
        ]
        for index, source in enumerate(external_sources)
    ]
    cms_feed = _feed_created_at(now, source=FeedSource.CMS)
    repository = resolve(client, container, FeedRepository)
    for feed in [cms_feed, *(feed for feeds in external_feeds for feed in feeds)]:
        run_in_app(client, lambda feed=feed: repository.create(feed))

    response = client.get("/feed/home")

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [
        feed.id.value for feeds in external_feeds for feed in feeds[:2]
    ]


def test_home_shows_two_feeds_of_each_source_after_scraping(client: TestClient) -> None:
    client.get("/feed/scrap")

    response = client.get("/feed/home")

    assert response.status_code == 200
    assert Counter(feed["source"] for feed in response.json()) == {
        "EL_MUNDO": 2,
        "EL_ESPANOL": 2,
        "EL_CONFIDENCIAL": 2,
        "LA_RAZON": 2,
        "LA_VANGUARDIA": 2,
    }


def test_home_answers_a_stale_front_page_as_it_is_without_scraping(
    container: AsyncContainer, client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    stale = _feed_created_at(datetime(2023, 6, 17, 14, 58, tzinfo=UTC), FeedSource.EL_MUNDO)
    repository = resolve(client, container, FeedRepository)
    run_in_app(client, lambda: repository.create(stale))

    response = client.get("/feed/home")
    # Lets a background run, if one had been started, reach the scraped sites.
    run_in_app(client, lambda: asyncio.sleep(0.1))

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [stale.id.value]
    assert front_pages_transport.requests == []
