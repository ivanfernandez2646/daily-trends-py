import asyncio
import logging
from datetime import UTC, datetime, timedelta

import pytest

from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_scrap import FeedScrap
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.blocking_feed_scrap import BlockingFeedScrap
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrap import StubFeedScrap
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
COOLDOWN = timedelta(minutes=5)


def _refresher(scraper: FeedScraper) -> FeedHomeRefresher:
    return FeedHomeRefresher(scraper, FixedClock(NOW), COOLDOWN)


def _scraper(scrap: FeedScrap, repository: FeedRepository | None = None) -> FeedScraper:
    return FeedScraper(repository or InMemoryFeedRepository(), [scrap])


async def test_request_starts_a_run_without_waiting_for_it() -> None:
    feeds = [FeedMother.random()]
    scrap = BlockingFeedScrap(feeds)
    repository = InMemoryFeedRepository()
    refresher = _refresher(_scraper(scrap, repository))

    refresher.request()
    await scrap.started.wait()
    saved_before_the_run_ends = list(repository.saved)
    scrap.release()
    await refresher.join()

    assert saved_before_the_run_ends == []
    assert repository.saved == feeds
    assert scrap.calls == 1


async def test_a_request_while_its_run_is_in_progress_is_ignored() -> None:
    scrap = BlockingFeedScrap([FeedMother.random()])
    refresher = _refresher(_scraper(scrap))
    refresher.request()
    await scrap.started.wait()

    refresher.request()
    scrap.release()
    await refresher.join()

    assert scrap.calls == 1


async def test_a_request_while_a_manual_run_is_in_progress_is_ignored() -> None:
    scrap = BlockingFeedScrap([FeedMother.random()])
    scraper = _scraper(scrap)
    refresher = _refresher(scraper)
    manual_run = asyncio.create_task(scraper.execute())
    await scrap.started.wait()

    refresher.request()
    scrap.release()
    await manual_run
    await refresher.join()

    assert scrap.calls == 1


async def test_a_new_request_after_a_run_finished_starts_another_run() -> None:
    scrap = StubFeedScrap()
    refresher = _refresher(_scraper(scrap))
    refresher.request()
    await refresher.join()

    refresher.request()
    await refresher.join()

    assert scrap.calls == 2


async def test_a_failing_run_is_logged_and_does_not_propagate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = RuntimeError("Mongo is down")
    repository = FailingFeedRepository(saves_before_failing=0, error=error)
    scrap = StubFeedScrap([FeedMother.random()])
    refresher = _refresher(_scraper(scrap, repository))

    refresher.request()
    await refresher.join()
    refresher.request()
    await refresher.join()

    assert [record.exc_info[1] for record in caplog.records if record.exc_info] == [error, error]
    assert all(record.levelno == logging.ERROR for record in caplog.records)
    assert scrap.calls == 2


async def test_aclose_cancels_the_run_in_progress() -> None:
    scrap = BlockingFeedScrap([FeedMother.random()])
    repository = InMemoryFeedRepository()
    scraper = _scraper(scrap, repository)
    refresher = _refresher(scraper)
    refresher.request()
    await scrap.started.wait()

    await refresher.aclose()
    scrap.release()
    await asyncio.sleep(0)

    assert repository.saved == []
    assert not scraper.is_running


async def test_join_and_aclose_without_a_run_return_at_once() -> None:
    refresher = _refresher(_scraper(StubFeedScrap()))

    await refresher.join()
    await refresher.aclose()
