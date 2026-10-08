import pytest

from daily_trends_py.contexts.cms.feeds.application.delete.feed_deleter import FeedDeleter
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


async def test_raises_feed_not_found_without_deleting_when_the_feed_does_not_exist() -> None:
    repository = InMemoryFeedRepository()
    id = FeedIdMother.random()

    with pytest.raises(FeedNotFound) as error:
        await FeedDeleter(repository).execute(id)

    assert str(error.value) == f"Feed with id <{id.value}> not found"
    assert repository.deleted == []


@pytest.mark.parametrize("source", list(FeedSource))
async def test_deletes_an_existing_feed_of_any_source(source: FeedSource) -> None:
    feed = FeedMother.random(source=source)
    repository = InMemoryFeedRepository([feed])

    await FeedDeleter(repository).execute(feed.id)

    assert repository.deleted == [feed]
    assert await repository.find(feed.id) is None
