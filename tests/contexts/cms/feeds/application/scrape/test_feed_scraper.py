import asyncio
from zoneinfo import ZoneInfo

import pytest

from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.errors import FeedAlreadyExists
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource, FeedTitle
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.blocking_feed_scrape import BlockingFeedScrape
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrape import StubFeedScrape

MADRID = ZoneInfo("Europe/Madrid")


async def test_creates_and_returns_every_feed_of_every_scraper_in_scraper_order() -> None:
    first_feeds = [FeedMother.random(), FeedMother.random()]
    second_feeds = [FeedMother.random()]
    scrapers = [StubFeedScrape(first_feeds), StubFeedScrape(second_feeds)]
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, scrapers, MADRID).execute()

    assert repository.created == [*first_feeds, *second_feeds]
    assert result == repository.created
    assert [scraper.calls for scraper in scrapers] == [1, 1]


async def test_drops_a_failing_scraper_and_saves_and_returns_the_others() -> None:
    feeds = [FeedMother.random(), FeedMother.random()]
    scrapers = [StubFeedScrape(error=RuntimeError("blocked")), StubFeedScrape(feeds)]
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, scrapers, MADRID).execute()

    assert repository.created == feeds
    assert result == feeds


async def test_returns_nothing_when_every_scraper_fails() -> None:
    scrapers = [StubFeedScrape(error=RuntimeError("blocked")) for _ in range(2)]
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, scrapers, MADRID).execute()

    assert result == []
    assert repository.created == []


async def test_saves_nothing_when_the_scrapers_return_nothing() -> None:
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, [StubFeedScrape(), StubFeedScrape()], MADRID).execute()

    assert result == []
    assert repository.created == []


async def test_creates_each_feed_with_its_own_id_without_looking_it_up() -> None:
    scraped = FeedMother.random()
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, [StubFeedScrape([scraped])], MADRID).execute()

    assert repository.created == [scraped]
    assert result == [scraped]
    assert repository.searched_ids == []


async def test_propagates_a_create_error_keeping_the_feeds_already_created() -> None:
    feeds = [FeedMother.random(), FeedMother.random(), FeedMother.random()]
    repository = FailingFeedRepository(
        creates_before_failing=1, error=RuntimeError("Mongo is down")
    )

    with pytest.raises(RuntimeError, match="Mongo is down"):
        await FeedScraper(repository, [StubFeedScrape(feeds)], MADRID).execute()

    assert repository.created == feeds[:1]


async def test_propagates_feed_already_exists_from_create_keeping_the_feeds_already_created() -> (
    None
):
    stored = FeedMother.random()
    first, clashing, last = (
        FeedMother.random(),
        FeedMother.random(id=stored.id),
        FeedMother.random(),
    )
    repository = InMemoryFeedRepository([stored])

    with pytest.raises(FeedAlreadyExists):
        await FeedScraper(repository, [StubFeedScrape([first, clashing, last])], MADRID).execute()

    assert repository.created == [first]
    assert await repository.find(stored.id) is stored


def _headline(source: FeedSource, title: str, created_at: str) -> Feed:
    return FeedMother.random(
        source=source,
        title=FeedTitle(title),
        created_at=FeedCreatedAtMother.create(created_at),
    )


async def test_skips_a_headline_already_stored_the_same_business_day() -> None:
    # 00:00 and 23:59:59.999 on 8 October in Madrid.
    stored = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-07T22:00:00.000Z")
    repeated = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-08T21:59:59.999Z")
    new = _headline(FeedSource.EL_MUNDO, "Another headline", "2026-10-08T12:00:00.000Z")
    repository = InMemoryFeedRepository([stored])

    result = await FeedScraper(repository, [StubFeedScrape([repeated, new])], MADRID).execute()

    assert repository.created == [new]
    assert result == [new]


async def test_saves_only_the_first_of_two_equal_headlines_in_the_same_run() -> None:
    first = _headline(FeedSource.EL_ESPANOL, "Same headline", "2026-10-08T10:00:00.000Z")
    second = _headline(FeedSource.EL_ESPANOL, "Same headline", "2026-10-08T10:00:00.001Z")
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, [StubFeedScrape([first, second])], MADRID).execute()

    assert repository.created == [first]
    assert result == [first]


async def test_saves_a_headline_stored_on_a_previous_business_day_or_by_another_source() -> None:
    # 23:59:59.999 on 7 October in Madrid.
    yesterday = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-07T21:59:59.999Z")
    other_source = _headline(FeedSource.CMS, "Same headline", "2026-10-08T09:00:00.000Z")
    scraped = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-08T10:00:00.000Z")
    repository = InMemoryFeedRepository([yesterday, other_source])

    result = await FeedScraper(repository, [StubFeedScrape([scraped])], MADRID).execute()

    assert result == [scraped]


@pytest.mark.parametrize(
    ("stored_at", "scraped_at", "saved"),
    [
        pytest.param(
            "2026-10-08T21:30:00.000Z",
            "2026-10-08T22:30:00.000Z",
            True,
            id="23:30 and 00:30 in Madrid, same UTC day",
        ),
        pytest.param(
            "2026-10-08T22:30:00.000Z",
            "2026-10-09T21:00:00.000Z",
            False,
            id="00:30 and 23:00 in Madrid, different UTC days",
        ),
        pytest.param(
            "2026-10-24T22:30:00.000Z",
            "2026-10-25T22:30:00.000Z",
            False,
            id="00:30 and 23:30 in Madrid on the 25-hour day",
        ),
        pytest.param(
            "2026-10-24T22:30:00.000Z",
            "2026-10-25T23:00:00.000Z",
            True,
            id="00:30 on the 25-hour day and midnight after it",
        ),
    ],
)
async def test_compares_headline_days_in_the_business_timezone(
    stored_at: str, scraped_at: str, saved: bool
) -> None:
    stored = _headline(FeedSource.EL_MUNDO, "Same headline", stored_at)
    scraped = _headline(FeedSource.EL_MUNDO, "Same headline", scraped_at)
    repository = InMemoryFeedRepository([stored])

    result = await FeedScraper(repository, [StubFeedScrape([scraped])], MADRID).execute()

    assert result == ([scraped] if saved else [])


async def _let_other_tasks_run() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


async def test_a_concurrent_run_waits_for_the_run_in_progress_and_skips_its_headlines() -> None:
    feeds = [FeedMother.random(), FeedMother.random()]
    scrape = BlockingFeedScrape(feeds)
    repository = InMemoryFeedRepository()
    scraper = FeedScraper(repository, [scrape], MADRID)
    first_run = asyncio.create_task(scraper.execute())
    await scrape.started.wait()

    second_run = asyncio.create_task(scraper.execute())
    await _let_other_tasks_run()
    calls_while_the_first_run_is_blocked = scrape.calls
    scrape.release()
    first, second = await asyncio.gather(first_run, second_run)

    assert calls_while_the_first_run_is_blocked == 1
    assert scrape.calls == 2
    assert first == feeds
    assert second == []
    assert repository.created == feeds


async def test_is_running_only_while_a_run_is_in_progress() -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    scraper = FeedScraper(InMemoryFeedRepository(), [scrape], MADRID)
    running_before = scraper.is_running

    run = asyncio.create_task(scraper.execute())
    await scrape.started.wait()
    running_during = scraper.is_running
    scrape.release()
    await run

    assert not running_before
    assert running_during
    assert not scraper.is_running


async def test_is_not_running_after_a_run_whose_create_raised() -> None:
    scrape = BlockingFeedScrape([FeedMother.random()])
    repository = FailingFeedRepository(
        creates_before_failing=0, error=RuntimeError("Mongo is down")
    )
    scraper = FeedScraper(repository, [scrape], MADRID)
    run = asyncio.create_task(scraper.execute())
    await scrape.started.wait()

    scrape.release()
    with pytest.raises(RuntimeError, match="Mongo is down"):
        await run

    assert not scraper.is_running
