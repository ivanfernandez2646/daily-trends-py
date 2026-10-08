from datetime import UTC, datetime, timedelta, timezone

import pytest

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    HOME_CRITERIA,
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrap import StubFeedScrap
from tests.contexts.cms.shared.domain.date_time_value_object_mother import (
    RequiredDateTimeValueObjectMother,
)
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
TODAY = "2026-10-08T08:00:00.000Z"
YESTERDAY = "2026-10-07T23:59:59.999Z"


def _feed_created_at(created_at: str) -> Feed:
    return FeedMother.random(
        source=FeedSource.EL_MUNDO,
        created_at=RequiredDateTimeValueObjectMother.create(created_at),
    )


def _searcher(
    repository: InMemoryFeedRepository, scrap: StubFeedScrap, now: datetime = NOW
) -> FeedHomeSearcher:
    return FeedHomeSearcher(repository, FeedScraper(repository, [scrap]), FixedClock(now))


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
    searcher = _searcher(repository, scrap)

    result = await searcher.execute()

    assert result == feeds
    assert scrap.calls == 0
    assert repository.searched_criteria == [HOME_CRITERIA]


async def test_scrapes_and_searches_again_when_the_newest_is_from_a_previous_day() -> None:
    stale = _feed_created_at(YESTERDAY)
    scraped = FeedMother.random()
    repository = InMemoryFeedRepository([stale])
    scrap = StubFeedScrap([scraped])
    searcher = _searcher(repository, scrap)

    result = await searcher.execute()

    assert result == [stale, scraped]
    assert scrap.calls == 1
    assert repository.searched_criteria == [HOME_CRITERIA, HOME_CRITERIA]


async def test_returns_nothing_without_scraping_when_there_are_no_feeds() -> None:
    repository = InMemoryFeedRepository()
    scrap = StubFeedScrap([FeedMother.random()])
    searcher = _searcher(repository, scrap)

    result = await searcher.execute()

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
    searcher = FeedHomeSearcher(repository, FeedScraper(repository, [scrap]), FixedClock(local_now))

    await searcher.execute()

    assert scrap.calls == expected_scrap_calls


async def test_returns_the_existing_feeds_and_retries_on_every_call_when_scraping_fails() -> None:
    stale = _feed_created_at(YESTERDAY)
    repository = InMemoryFeedRepository([stale])
    scrap = StubFeedScrap(error=RuntimeError("blocked"))
    searcher = _searcher(repository, scrap)

    first = await searcher.execute()
    second = await searcher.execute()

    assert first == second == [stale]
    assert scrap.calls == 2


async def test_propagates_a_save_error_from_scraping() -> None:
    repository = FailingFeedRepository(
        saves_before_failing=0,
        error=RuntimeError("Mongo is down"),
        feeds=[_feed_created_at(YESTERDAY)],
    )
    scrap = StubFeedScrap([FeedMother.random()])
    searcher = _searcher(repository, scrap)

    with pytest.raises(RuntimeError, match="Mongo is down"):
        await searcher.execute()
