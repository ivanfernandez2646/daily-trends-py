from datetime import UTC, datetime, timedelta, timezone

import pytest

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    HOME_CRITERIA,
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_scrap import FeedScrap
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.blocking_feed_scrap import BlockingFeedScrap
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrap import StubFeedScrap
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
TODAY = "2026-10-08T08:00:00.000Z"
YESTERDAY = "2026-10-07T23:59:59.999Z"
COOLDOWN = timedelta(minutes=5)


def _feed_created_at(created_at: str) -> Feed:
    return FeedMother.random(
        source=FeedSource.EL_MUNDO,
        created_at=FeedCreatedAtMother.create(created_at),
    )


def _searcher(
    repository: FeedRepository, scrap: FeedScrap, now: datetime = NOW
) -> tuple[FeedHomeSearcher, FeedHomeRefresher]:
    clock = FixedClock(now)
    refresher = FeedHomeRefresher(FeedScraper(repository, [scrap]), clock, COOLDOWN)
    return FeedHomeSearcher(repository, refresher, clock), refresher


def test_home_criteria_searches_the_ten_newest_external_feeds() -> None:
    assert HOME_CRITERIA == {
        "filter": [{"source": FeedSource.EL_MUNDO}, {"source": FeedSource.EL_ESPANOL}],
        "sort": {"createdAt": "desc"},
        "limit": 10,
    }


async def test_returns_the_feeds_without_scraping_when_the_newest_is_from_today() -> None:
    feeds = [_feed_created_at(TODAY), _feed_created_at(YESTERDAY)]
    repository = InMemoryFeedRepository(feeds)
    scrap = StubFeedScrap([FeedMother.random()])
    searcher, refresher = _searcher(repository, scrap)

    result = await searcher.execute()
    await refresher.join()

    assert result == feeds
    assert scrap.calls == 0
    assert repository.searched_criteria == [HOME_CRITERIA]


async def test_returns_the_stale_feeds_at_once_and_scrapes_in_the_background() -> None:
    stale = _feed_created_at(YESTERDAY)
    scraped = FeedMother.random()
    repository = InMemoryFeedRepository([stale])
    scrap = BlockingFeedScrap([scraped])
    searcher, refresher = _searcher(repository, scrap)

    result = await searcher.execute()
    await scrap.started.wait()
    scrap.release()
    await refresher.join()

    assert result == [stale]
    assert repository.searched_criteria == [HOME_CRITERIA]
    assert repository.saved == [scraped]


async def test_returns_nothing_without_scraping_when_there_are_no_feeds() -> None:
    repository = InMemoryFeedRepository()
    scrap = StubFeedScrap([FeedMother.random()])
    searcher, refresher = _searcher(repository, scrap)

    result = await searcher.execute()
    await refresher.join()

    assert result == []
    assert scrap.calls == 0


@pytest.mark.parametrize(
    ("newest_created_at", "expected_scrap_calls"),
    [
        pytest.param("2026-10-07T22:15:00.000Z", 0, id="same local day"),
        pytest.param("2026-10-07T21:59:00.000Z", 1, id="previous local day"),
    ],
)
async def test_compares_days_in_the_local_zone_of_the_clock(
    newest_created_at: str, expected_scrap_calls: int
) -> None:
    local_now = datetime(2026, 10, 8, 0, 30, tzinfo=timezone(timedelta(hours=2)))
    repository = InMemoryFeedRepository([_feed_created_at(newest_created_at)])
    scrap = StubFeedScrap()
    searcher, refresher = _searcher(repository, scrap, local_now)

    await searcher.execute()
    await refresher.join()

    assert scrap.calls == expected_scrap_calls


async def test_returns_the_stale_feeds_when_the_background_scraping_fails() -> None:
    stale = _feed_created_at(YESTERDAY)
    repository = FailingFeedRepository(
        saves_before_failing=0, error=RuntimeError("Mongo is down"), feeds=[stale]
    )
    scrap = StubFeedScrap([FeedMother.random()])
    searcher, refresher = _searcher(repository, scrap)

    result = await searcher.execute()
    await refresher.join()

    assert result == [stale]
    assert scrap.calls == 1
