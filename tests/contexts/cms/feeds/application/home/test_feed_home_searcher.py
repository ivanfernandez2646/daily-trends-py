from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    HOME_CRITERIA,
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


def test_home_criteria_searches_the_ten_newest_external_feeds() -> None:
    assert HOME_CRITERIA == {
        "filter": [
            {"source": FeedSource.EL_MUNDO},
            {"source": FeedSource.EL_ESPANOL},
        ],
        "sort": {"createdAt": "desc"},
        "limit": 10,
    }


async def test_returns_the_feeds_found_with_the_home_criteria() -> None:
    feeds = [
        FeedMother.random(source=FeedSource.EL_MUNDO),
        FeedMother.random(source=FeedSource.EL_ESPANOL),
    ]
    repository = InMemoryFeedRepository(feeds)
    searcher = FeedHomeSearcher(repository)

    result = await searcher.execute()

    assert result == feeds
    assert repository.searched_criteria == [HOME_CRITERIA]


async def test_returns_nothing_when_there_are_no_feeds() -> None:
    repository = InMemoryFeedRepository()
    searcher = FeedHomeSearcher(repository)

    result = await searcher.execute()

    assert result == []
