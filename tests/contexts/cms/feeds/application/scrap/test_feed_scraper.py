import pytest

from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
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


async def test_regenerates_and_returns_the_id_of_a_feed_whose_id_already_exists() -> None:
    existing = FeedMother.random()
    scraped = FeedMother.random(id=existing.id)
    repository = InMemoryFeedRepository([existing])

    result = await FeedScraper(repository, [StubFeedScrap([scraped])]).execute()

    [saved] = repository.saved
    assert result == [saved]
    assert saved.id != existing.id
    assert {**saved.to_primitives(), "id": scraped.id.value} == scraped.to_primitives()


async def test_propagates_a_save_error_keeping_the_feeds_already_saved() -> None:
    feeds = [FeedMother.random(), FeedMother.random(), FeedMother.random()]
    repository = FailingFeedRepository(saves_before_failing=1, error=RuntimeError("Mongo is down"))

    with pytest.raises(RuntimeError, match="Mongo is down"):
        await FeedScraper(repository, [StubFeedScrap(feeds)]).execute()

    assert repository.saved == feeds[:1]
