from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_scrape import FeedScrape
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.blocking_feed_scrape import BlockingFeedScrape
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrape import StubFeedScrape
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
TODAY = "2026-10-08T08:00:00.000Z"
YESTERDAY = "2026-10-07T23:59:59.999Z"
COOLDOWN = timedelta(minutes=5)
MADRID = ZoneInfo("Europe/Madrid")
HOME_SOURCES = [
    FeedSource.EL_MUNDO,
    FeedSource.EL_ESPANOL,
    FeedSource.EL_CONFIDENCIAL,
    FeedSource.LA_RAZON,
    FeedSource.LA_VANGUARDIA,
]


def _feed_created_at(created_at: str) -> Feed:
    return FeedMother.random(
        source=FeedSource.EL_MUNDO,
        created_at=FeedCreatedAtMother.create(created_at),
    )


def _searcher(
    repository: FeedRepository, scrape: FeedScrape, now: datetime = NOW
) -> tuple[FeedHomeSearcher, FeedHomeRefresher]:
    clock = FixedClock(now)
    refresher = FeedHomeRefresher(FeedScraper(repository, [scrape], MADRID), clock, COOLDOWN)
    return FeedHomeSearcher(repository, refresher, clock), refresher


def _feed(source: FeedSource, created_at: str) -> Feed:
    return FeedMother.random(source=source, created_at=FeedCreatedAtMother.create(created_at))


def _newest_first(feeds: list[Feed]) -> list[Feed]:
    return sorted(feeds, key=lambda feed: feed.created_at.value, reverse=True)


async def _search(feeds: list[Feed]) -> tuple[list[Feed], StubFeedScrape]:
    scrape = StubFeedScrape()
    searcher, refresher = _searcher(InMemoryFeedRepository(feeds), scrape)
    result = await searcher.execute()
    await refresher.join()
    return result, scrape


async def test_returns_the_two_newest_feeds_of_each_home_source_newest_first() -> None:
    # Each source is an hour older than the previous one, so El Mundo's third feed is newer
    # than every feed of the other sources.
    feeds = {
        source: [
            _feed(source, f"2026-10-08T{10 - index:02}:{minute:02}:00.000Z")
            for minute in (20, 10, 0)
        ]
        for index, source in enumerate(HOME_SOURCES)
    }

    result, _ = await _search([feed for source_feeds in feeds.values() for feed in source_feeds])

    assert result == _newest_first(
        [feed for source_feeds in feeds.values() for feed in source_feeds[:2]]
    )


async def test_returns_the_ten_newest_feeds_when_only_one_source_has_feeds() -> None:
    feeds = [_feed(FeedSource.EL_MUNDO, f"2026-10-08T{hour:02}:00:00.000Z") for hour in range(12)]

    result, _ = await _search(feeds)

    assert result == _newest_first(feeds)[:10]


async def test_fills_the_slots_of_sources_with_fewer_than_two_feeds_with_the_newest_others() -> (
    None
):
    el_mundo = [
        _feed(FeedSource.EL_MUNDO, f"2026-10-08T{hour:02}:00:00.000Z")
        for hour in (11, 10, 9, 8, 7, 6)
    ]
    el_espanol = _feed(FeedSource.EL_ESPANOL, "2026-10-08T05:00:00.000Z")
    la_razon = [_feed(FeedSource.LA_RAZON, f"2026-10-08T{hour:02}:00:00.000Z") for hour in (4, 3)]
    la_vanguardia = [
        _feed(FeedSource.LA_VANGUARDIA, f"2026-10-08T{hour:02}:00:00.000Z") for hour in (2, 1)
    ]

    result, _ = await _search([*el_mundo, el_espanol, *la_razon, *la_vanguardia])

    assert result == [*el_mundo[:5], el_espanol, *la_razon, *la_vanguardia]


async def test_returns_every_home_feed_when_there_are_fewer_than_ten() -> None:
    feeds = [
        _feed(source, f"2026-10-08T{hour:02}:00:00.000Z")
        for hour, source in enumerate([FeedSource.EL_MUNDO, *HOME_SOURCES])
    ]

    result, _ = await _search(feeds)

    assert result == _newest_first(feeds)


async def test_keeps_the_slots_of_a_source_whose_newest_feeds_are_old() -> None:
    week_old = [_feed(FeedSource.LA_RAZON, f"2026-10-01T{hour:02}:00:00.000Z") for hour in (9, 8)]
    recent = {
        source: [
            _feed(source, f"2026-10-08T{10 - index:02}:{minute:02}:00.000Z")
            for minute in (20, 10, 0)
        ]
        for index, source in enumerate(HOME_SOURCES)
        if source != FeedSource.LA_RAZON
    }

    result, scrape = await _search(
        [*week_old, *(feed for source_feeds in recent.values() for feed in source_feeds)]
    )

    assert result == _newest_first(
        [*week_old, *(feed for source_feeds in recent.values() for feed in source_feeds[:2])]
    )
    assert scrape.calls == 0


async def test_never_returns_cms_or_el_pais_feeds() -> None:
    home_feed = _feed(FeedSource.EL_MUNDO, "2026-10-08T08:00:00.000Z")
    excluded = [
        _feed(source, "2026-10-08T11:00:00.000Z") for source in (FeedSource.CMS, FeedSource.EL_PAIS)
    ]

    result, _ = await _search([*excluded, home_feed])

    assert result == [home_feed]


async def test_returns_the_feeds_without_scraping_when_the_newest_is_from_today() -> None:
    feeds = [_feed_created_at(TODAY), _feed_created_at(YESTERDAY)]
    repository = InMemoryFeedRepository(feeds)
    scrape = StubFeedScrape([FeedMother.random()])
    searcher, refresher = _searcher(repository, scrape)

    result = await searcher.execute()
    await refresher.join()

    assert result == feeds
    assert scrape.calls == 0


async def test_returns_the_stale_feeds_at_once_and_scrapes_in_the_background() -> None:
    stale = _feed_created_at(YESTERDAY)
    scraped = FeedMother.random()
    repository = InMemoryFeedRepository([stale])
    scrape = BlockingFeedScrape([scraped])
    searcher, refresher = _searcher(repository, scrape)

    result = await searcher.execute()
    await scrape.started.wait()
    scrape.release()
    await refresher.join()

    assert result == [stale]
    assert repository.created == [scraped]


async def test_returns_nothing_without_scraping_when_there_are_no_feeds() -> None:
    repository = InMemoryFeedRepository()
    scrape = StubFeedScrape([FeedMother.random()])
    searcher, refresher = _searcher(repository, scrape)

    result = await searcher.execute()
    await refresher.join()

    assert result == []
    assert scrape.calls == 0


@pytest.mark.parametrize(
    ("newest_created_at", "expected_scrape_calls"),
    [
        pytest.param("2026-10-07T22:15:00.000Z", 0, id="same local day"),
        pytest.param("2026-10-07T21:59:00.000Z", 1, id="previous local day"),
    ],
)
async def test_compares_days_in_the_local_zone_of_the_clock(
    newest_created_at: str, expected_scrape_calls: int
) -> None:
    local_now = datetime(2026, 10, 8, 0, 30, tzinfo=timezone(timedelta(hours=2)))
    repository = InMemoryFeedRepository([_feed_created_at(newest_created_at)])
    scrape = StubFeedScrape()
    searcher, refresher = _searcher(repository, scrape, local_now)

    await searcher.execute()
    await refresher.join()

    assert scrape.calls == expected_scrape_calls


@pytest.mark.parametrize(
    ("local_now", "expected_scrape_calls"),
    [
        pytest.param(datetime(2026, 10, 9, 10, 0, tzinfo=MADRID), 0, id="same business day"),
        pytest.param(datetime(2026, 10, 10, 10, 0, tzinfo=MADRID), 1, id="next business day"),
    ],
)
async def test_compares_days_in_the_business_timezone_across_utc_midnight(
    local_now: datetime, expected_scrape_calls: int
) -> None:
    # 00:30 on 9 October in Madrid, still 8 October in UTC.
    repository = InMemoryFeedRepository([_feed_created_at("2026-10-08T22:30:00.000Z")])
    scrape = StubFeedScrape()
    searcher, refresher = _searcher(repository, scrape, local_now)

    await searcher.execute()
    await refresher.join()

    assert scrape.calls == expected_scrape_calls


async def test_returns_the_stale_feeds_when_the_background_scraping_fails() -> None:
    stale = _feed_created_at(YESTERDAY)
    repository = FailingFeedRepository(
        creates_before_failing=0, error=RuntimeError("Mongo is down"), feeds=[stale]
    )
    scrape = StubFeedScrape([FeedMother.random()])
    searcher, refresher = _searcher(repository, scrape)

    result = await searcher.execute()
    await refresher.join()

    assert result == [stale]
    assert scrape.calls == 1
