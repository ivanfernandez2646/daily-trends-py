import pytest

from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.failing_feed_repository import FailingFeedRepository
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.feeds.fakes.stub_feed_scrap import StubFeedScrap


async def test_saves_and_returns_every_feed_of_every_scraper_in_scraper_order() -> None:
    first_feeds = [FeedMother.random(), FeedMother.random()]
    second_feeds = [FeedMother.random()]
    scrapers = [StubFeedScrap(first_feeds), StubFeedScrap(second_feeds)]
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, scrapers).execute()

    assert repository.saved == [*first_feeds, *second_feeds]
    assert result == repository.saved
    assert [scraper.calls for scraper in scrapers] == [1, 1]


async def test_drops_a_failing_scraper_and_saves_and_returns_the_others() -> None:
    feeds = [FeedMother.random(), FeedMother.random()]
    scrapers = [StubFeedScrap(error=RuntimeError("blocked")), StubFeedScrap(feeds)]
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, scrapers).execute()

    assert repository.saved == feeds
    assert result == feeds


async def test_returns_nothing_when_every_scraper_fails() -> None:
    scrapers = [StubFeedScrap(error=RuntimeError("blocked")) for _ in range(2)]
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, scrapers).execute()

    assert result == []
    assert repository.saved == []


async def test_saves_nothing_when_the_scrapers_return_nothing() -> None:
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, [StubFeedScrap(), StubFeedScrap()]).execute()

    assert result == []
    assert repository.saved == []


async def test_saves_each_feed_with_its_own_id_without_looking_it_up() -> None:
    scraped = FeedMother.random()
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, [StubFeedScrap([scraped])]).execute()

    assert repository.saved == [scraped]
    assert result == [scraped]
    assert repository.searched_ids == []


async def test_propagates_a_save_error_keeping_the_feeds_already_saved() -> None:
    feeds = [FeedMother.random(), FeedMother.random(), FeedMother.random()]
    repository = FailingFeedRepository(saves_before_failing=1, error=RuntimeError("Mongo is down"))

    with pytest.raises(RuntimeError, match="Mongo is down"):
        await FeedScraper(repository, [StubFeedScrap(feeds)]).execute()

    assert repository.saved == feeds[:1]


def _headline(source: FeedSource, title: str, created_at: str) -> Feed:
    return FeedMother.random(
        source=source,
        title=FeedTitle(title),
        created_at=FeedCreatedAtMother.create(created_at),
    )


async def test_skips_a_headline_already_stored_the_same_utc_day() -> None:
    stored = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-08T00:00:00.000Z")
    repeated = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-08T23:59:59.999Z")
    new = _headline(FeedSource.EL_MUNDO, "Another headline", "2026-10-08T12:00:00.000Z")
    repository = InMemoryFeedRepository([stored])

    result = await FeedScraper(repository, [StubFeedScrap([repeated, new])]).execute()

    assert repository.saved == [new]
    assert result == [new]


async def test_saves_only_the_first_of_two_equal_headlines_in_the_same_run() -> None:
    first = _headline(FeedSource.EL_ESPANOL, "Same headline", "2026-10-08T10:00:00.000Z")
    second = _headline(FeedSource.EL_ESPANOL, "Same headline", "2026-10-08T10:00:00.001Z")
    repository = InMemoryFeedRepository()

    result = await FeedScraper(repository, [StubFeedScrap([first, second])]).execute()

    assert repository.saved == [first]
    assert result == [first]


async def test_saves_a_headline_stored_on_a_previous_utc_day_or_by_another_source() -> None:
    yesterday = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-07T23:59:59.999Z")
    other_source = _headline(FeedSource.CMS, "Same headline", "2026-10-08T09:00:00.000Z")
    scraped = _headline(FeedSource.EL_MUNDO, "Same headline", "2026-10-08T10:00:00.000Z")
    repository = InMemoryFeedRepository([yesterday, other_source])

    result = await FeedScraper(repository, [StubFeedScrap([scraped])]).execute()

    assert result == [scraped]
