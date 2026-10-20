from datetime import UTC, datetime

import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from tests.apps.cms_backend.conftest import resolve, run_in_app
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.scrape_fixtures import EVERY_FRONT_PAGE_HOST, FrontPagesTransport

pytestmark = pytest.mark.integration

scenarios("features/scrap-feed.feature")

OTHER_SOURCES_THAN_EL_MUNDO = ["EL_ESPANOL", "EL_CONFIDENCIAL", "LA_RAZON", "LA_VANGUARDIA"]


def _sources(feeds: list[dict[str, object]]) -> list[object]:
    return sorted({feed["source"] for feed in feeds}, key=str)


def test_scraping_reads_the_five_front_pages(
    client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert {request.url.host for request in front_pages_transport.requests} >= {
        "www.elmundo.es",
        "www.elespanol.com",
        "www.elconfidencial.com",
        "www.larazon.es",
        "www.lavanguardia.com",
    }
    scraped = response.json()
    assert len(scraped) == 25
    assert _sources(scraped) == sorted([*OTHER_SOURCES_THAN_EL_MUNDO, "EL_MUNDO"])


@pytest.mark.parametrize(
    "front_pages_transport", [FrontPagesTransport(failing_hosts={"elmundo.es"})]
)
def test_scraping_stores_and_returns_the_other_sources_when_one_fails(
    client: TestClient,
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    scraped = response.json()
    assert len(scraped) == 20
    assert _sources(scraped) == sorted(OTHER_SOURCES_THAN_EL_MUNDO)
    stored = client.get("/feed/list").json()
    assert sorted(feed["id"] for feed in stored) == sorted(feed["id"] for feed in scraped)


@pytest.mark.parametrize(
    "front_pages_transport",
    [FrontPagesTransport(failing_hosts=EVERY_FRONT_PAGE_HOST)],
)
def test_scraping_answers_an_empty_array_and_stores_nothing_when_every_source_fails(
    client: TestClient,
) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert response.json() == []
    assert client.get("/feed/list").json() == []


def test_scraping_identifies_itself_with_a_user_agent(
    client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    client.get("/feed/scrap")

    assert front_pages_transport.requests
    assert {request.headers["User-Agent"] for request in front_pages_transport.requests} == {
        "daily-trends-py"
    }


@pytest.mark.parametrize(
    "front_pages_transport", [FrontPagesTransport(timing_out_hosts={"www.elmundo.es"})]
)
def test_scraping_returns_the_other_sources_when_one_times_out(client: TestClient) -> None:
    response = client.get("/feed/scrap")

    assert response.status_code == 200
    scraped = response.json()
    assert len(scraped) == 20
    assert _sources(scraped) == sorted(OTHER_SOURCES_THAN_EL_MUNDO)


def test_scraping_after_a_background_run_saves_only_what_that_run_did_not(
    container: AsyncContainer, client: TestClient
) -> None:
    stale = FeedMother.random(
        source=FeedSource.EL_MUNDO,
        created_at=FeedCreatedAtMother.create(datetime(2023, 6, 17, tzinfo=UTC)),
    )
    repository = resolve(client, container, FeedRepository)
    run_in_app(client, lambda: repository.create(stale))
    client.get("/feed/home")
    refresher = resolve(client, container, FeedHomeRefresher)
    run_in_app(client, refresher.join)

    response = client.get("/feed/scrap")

    assert response.status_code == 200
    assert response.json() == []
    assert len(client.get("/feed/list").json()) == 26
