import asyncio
import logging
from datetime import UTC, datetime, timedelta

import pytest

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_scrape import FeedScrape
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.blocking_feed_scrape import BlockingFeedScrape
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrape import StubFeedScrape
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
COOLDOWN = timedelta(minutes=5)


def _refresher(scraper: FeedScraper, clock: FixedClock | None = None) -> FeedHomeRefresher:
    return FeedHomeRefresher(scraper, clock or FixedClock(NOW), COOLDOWN)


def _scraper(scrape: FeedScrape, repository: FeedRepository | None = None) -> FeedScraper:
    return FeedScraper(repository or InMemoryFeedRepository(), [scrape], UTC)


async def test_request_starts_a_run_without_waiting_for_it() -> None:
    feeds = [FeedMother.random()]
    scrape = BlockingFeedScrape(feeds)
    repository = InMemoryFeedRepository()
    refresher = _refresher(_scraper(scrape, repository))

    refresher.request()
    await scrape.started.wait()
    created_before_the_run_ends = list(repository.created)
    scrape.release()
    await refresher.join()

    assert created_before_the_run_ends == []
    assert repository.created == feeds
    assert scrape.calls == 1


async def test_a_request_while_its_run_is_in_progress_is_ignored() -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    refresher = _refresher(_scraper(scrape))
    refresher.request()
    await scrape.started.wait()

    refresher.request()
    scrape.release()
    await refresher.join()

    assert scrape.calls == 1


async def test_a_request_while_a_manual_run_is_in_progress_is_ignored() -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    scraper = _scraper(scrape)
    refresher = _refresher(scraper)
    manual_run = asyncio.create_task(scraper.execute())
    await scrape.started.wait()

    refresher.request()
    scrape.release()
    await manual_run
    await refresher.join()

    assert scrape.calls == 1


async def test_a_new_request_once_the_cooldown_has_passed_starts_another_run() -> None:
    scrape = StubFeedScrape()
    clock = FixedClock(NOW)
    refresher = _refresher(_scraper(scrape), clock)
    refresher.request()
    await refresher.join()

    clock.advance(COOLDOWN)
    refresher.request()
    await refresher.join()

    assert scrape.calls == 2


@pytest.mark.parametrize(
    "create_error",
    [
        pytest.param(None, id="after a successful run"),
        pytest.param(RuntimeError("blocked"), id="after a failing run"),
    ],
)
async def test_a_request_within_the_cooldown_of_the_last_run_end_is_ignored(
    create_error: Exception | None,
) -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    clock = FixedClock(NOW)
    repository = (
        FailingFeedRepository(creates_before_failing=0, error=create_error)
        if create_error
        else InMemoryFeedRepository()
    )
    refresher = _refresher(_scraper(scrape, repository), clock)
    refresher.request()
    await scrape.started.wait()
    clock.advance(timedelta(minutes=1))
    scrape.release()
    await refresher.join()

    clock.advance(COOLDOWN - timedelta(microseconds=1))
    refresher.request()
    await refresher.join()
    calls_within_the_cooldown = scrape.calls
    clock.advance(timedelta(microseconds=1))
    refresher.request()
    await refresher.join()

    assert calls_within_the_cooldown == 1
    assert scrape.calls == 2


async def test_a_manual_run_is_not_blocked_by_the_cooldown() -> None:
    scrape = StubFeedScrape()
    scraper = _scraper(scrape)
    refresher = _refresher(scraper)
    refresher.request()
    await refresher.join()

    await scraper.execute()
    calls_after_the_manual_run = scrape.calls

    assert calls_after_the_manual_run == 2


async def test_a_manual_run_does_not_start_the_cooldown() -> None:
    scrape = StubFeedScrape()
    scraper = _scraper(scrape)
    refresher = _refresher(scraper)
    await scraper.execute()

    refresher.request()
    await refresher.join()

    assert scrape.calls == 2


async def test_a_failing_run_is_logged_and_does_not_propagate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = RuntimeError("Mongo is down")
    repository = FailingFeedRepository(creates_before_failing=0, error=error)
    scrape = StubFeedScrape([FeedMother.random()])
    refresher = _refresher(_scraper(scrape, repository))

    refresher.request()
    await refresher.join()

    assert [record.exc_info[1] for record in caplog.records if record.exc_info] == [error]
    assert all(record.levelno == logging.ERROR for record in caplog.records)
    assert scrape.calls == 1


async def test_aclose_cancels_the_run_in_progress() -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    repository = InMemoryFeedRepository()
    scraper = _scraper(scrape, repository)
    refresher = _refresher(scraper)
    refresher.request()
    await scrape.started.wait()

    await refresher.aclose()
    scrape.release()
    await asyncio.sleep(0)

    assert repository.created == []
    assert not scraper.is_running


async def test_join_and_aclose_without_a_run_return_at_once() -> None:
    refresher = _refresher(_scraper(StubFeedScrape()))

    await refresher.join()
    await refresher.aclose()
