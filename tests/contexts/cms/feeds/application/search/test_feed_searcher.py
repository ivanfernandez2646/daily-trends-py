from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import FeedSearcher
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


async def test_returns_the_feeds_found_with_the_given_criteria() -> None:
    feeds = [FeedMother.random(), FeedMother.random()]
    repository = InMemoryFeedRepository(feeds)
    searcher = FeedSearcher(repository)
    criteria: Criteria = {"filter": [{"source": "CMS"}], "sort": {"createdAt": "desc"}, "limit": 2}

    result = await searcher.execute(criteria)

    assert result == feeds
    assert repository.searched_criteria == [criteria]


async def test_searches_without_criteria_when_none_is_given() -> None:
    repository = InMemoryFeedRepository()
    searcher = FeedSearcher(repository)

    result = await searcher.execute()

    assert result == []
    assert repository.searched_criteria == [None]
