import pytest

from daily_trends_py.contexts.cms.feeds.application.find.feed_finder import FeedFinder
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


async def test_returns_the_feed_when_it_exists() -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])
    finder = FeedFinder(repository)

    result = await finder.execute(feed.id)

    assert result is feed
    assert repository.searched_ids == [feed.id]


async def test_raises_feed_not_found_when_the_feed_does_not_exist() -> None:
    id = FeedIdMother.random()
    finder = FeedFinder(InMemoryFeedRepository())

    with pytest.raises(FeedNotFound) as error:
        await finder.execute(id)

    assert str(error.value) == f"Feed with id <{id.value}> not found"
