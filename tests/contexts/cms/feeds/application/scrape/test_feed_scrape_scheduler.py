import asyncio
import logging
from datetime import UTC, timedelta

import pytest

from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scrape_scheduler import (
    FeedScrapeScheduler,
)
from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.feed_scrape import FeedScrape
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.blocking_feed_scrape import BlockingFeedScrape
from tests.contexts.cms.feeds.fakes.controlled_wait import ControlledWait
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrape import StubFeedScrape

INTERVAL = timedelta(hours=2)


def _scraper(scrape: FeedScrape, repository: FeedRepository | None = None) -> FeedScraper:
    return FeedScraper(repository or InMemoryFeedRepository(), [scrape], UTC)


async def _let_other_tasks_run() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


async def test_runs_at_once_then_one_interval_after_each_run_ends() -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(_scraper(scrape), INTERVAL, wait)

    scheduler.start()
    await scrape.started.wait()
    waits_while_the_first_run_is_blocked = list(wait.intervals)
    scrape.release()
    await wait.reached(1)
    calls_while_waiting = scrape.calls
    await wait.release()
    await wait.reached(2)
    await scheduler.aclose()

    assert waits_while_the_first_run_is_blocked == []
    assert calls_while_waiting == 1
    assert scrape.calls == 2
    assert wait.intervals == [INTERVAL, INTERVAL]


async def test_skips_a_run_that_is_due_while_a_manual_run_is_in_progress(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    scrape = BlockingFeedScrape([FeedMother.random()])
    scraper = _scraper(scrape)
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(scraper, INTERVAL, wait)
    manual_run = asyncio.create_task(scraper.execute())
    await scrape.started.wait()

    scheduler.start()
    await wait.reached(1)
    scrape.release()
    await manual_run
    await scheduler.aclose()

    assert scrape.calls == 1
    assert wait.intervals == [INTERVAL]
    assert "Scheduled scraping skipped" in caplog.text


async def test_a_manual_run_does_not_move_the_next_scheduled_run() -> None:
    scrape = StubFeedScrape([FeedMother.random()])
    scraper = _scraper(scrape)
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(scraper, INTERVAL, wait)
    scheduler.start()
    await wait.reached(1)

    await scraper.execute()
    await _let_other_tasks_run()
    calls_after_the_manual_run = scrape.calls
    await wait.release()
    await wait.reached(2)
    await scheduler.aclose()

    assert calls_after_the_manual_run == 2
    assert scrape.calls == 3
    assert wait.intervals == [INTERVAL, INTERVAL]


async def test_a_manual_run_during_a_scheduled_run_waits_for_it_and_saves_nothing_new() -> None:
    feeds = [FeedMother.random(), FeedMother.random()]
    scrape = BlockingFeedScrape(feeds)
    repository = InMemoryFeedRepository()
    scraper = _scraper(scrape, repository)
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(scraper, INTERVAL, wait)
    scheduler.start()
    await scrape.started.wait()

    manual_run = asyncio.create_task(scraper.execute())
    scrape.release()
    saved_by_the_manual_run = await manual_run
    await scheduler.aclose()

    assert saved_by_the_manual_run == []
    assert repository.created == feeds


async def test_a_failing_run_is_logged_and_the_schedule_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scrape = StubFeedScrape([FeedMother.random()])
    repository = FailingFeedRepository(
        creates_before_failing=0, error=RuntimeError("Mongo is down")
    )
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(_scraper(scrape, repository), INTERVAL, wait)

    scheduler.start()
    await wait.reached(1)
    await wait.release()
    await wait.reached(2)
    await scheduler.aclose()

    assert scrape.calls == 2
    failures = [record for record in caplog.records if record.exc_info]
    assert [record.getMessage() for record in failures] == ["Scheduled scraping failed"] * 2


async def test_logs_how_many_feeds_each_run_saved(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    scrape = StubFeedScrape([FeedMother.random(), FeedMother.random()])
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(_scraper(scrape), INTERVAL, wait)

    scheduler.start()
    await wait.reached(1)
    await wait.release()
    await wait.reached(2)
    await scheduler.aclose()

    assert [record.getMessage() for record in caplog.records if "saved" in record.getMessage()] == [
        "Scheduled scraping saved 2 feeds",
        "Scheduled scraping saved 0 feeds",
    ]


async def test_closing_while_waiting_starts_no_further_run() -> None:
    scrape = StubFeedScrape([FeedMother.random()])
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(_scraper(scrape), INTERVAL, wait)
    scheduler.start()
    await wait.reached(1)

    await scheduler.aclose()
    await wait.release()
    await _let_other_tasks_run()

    assert scrape.calls == 1
    assert wait.intervals == [INTERVAL]


async def test_closing_while_running_cancels_the_run_and_starts_no_further_one() -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    repository = InMemoryFeedRepository()
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(_scraper(scrape, repository), INTERVAL, wait)
    scheduler.start()
    await scrape.started.wait()

    await scheduler.aclose()
    scrape.release()
    await _let_other_tasks_run()

    assert scrape.calls == 1
    assert repository.created == []
    assert wait.intervals == []


async def test_starting_twice_runs_one_schedule() -> None:
    scrape = StubFeedScrape([FeedMother.random()])
    wait = ControlledWait()
    scheduler = FeedScrapeScheduler(_scraper(scrape), INTERVAL, wait)

    scheduler.start()
    scheduler.start()
    await wait.reached(1)
    await _let_other_tasks_run()
    await scheduler.aclose()

    assert scrape.calls == 1
    assert wait.intervals == [INTERVAL]


async def test_closing_without_starting_returns_at_once() -> None:
    scheduler = FeedScrapeScheduler(_scraper(StubFeedScrape()), INTERVAL, ControlledWait())

    await scheduler.aclose()
