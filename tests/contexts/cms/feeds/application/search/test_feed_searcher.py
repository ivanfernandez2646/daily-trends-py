from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import FeedSearcher
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


async def test_returns_the_feeds_that_match_the_criteria_in_order_and_limited() -> None:
    older = FeedMother.random(
        source=FeedSource.CMS, created_at=FeedCreatedAtMother.create("2026-10-01T10:00:00.000Z")
    )
    newer = FeedMother.random(
        source=FeedSource.CMS, created_at=FeedCreatedAtMother.create("2026-10-02T10:00:00.000Z")
    )
    newest = FeedMother.random(
        source=FeedSource.CMS, created_at=FeedCreatedAtMother.create("2026-10-03T10:00:00.000Z")
    )
    other_source = FeedMother.random(source=FeedSource.EL_PAIS)
    searcher = FeedSearcher(InMemoryFeedRepository([older, other_source, newest, newer]))

    result = await searcher.execute(
        FeedCriteria(
            filters=(Filter("source", FeedSource.CMS),),
            order=Order("created_at", "desc"),
            limit=2,
        )
    )

    assert result == [newest, newer]


async def test_returns_every_feed_without_filters() -> None:
    feeds = [FeedMother.random(), FeedMother.random()]
    searcher = FeedSearcher(InMemoryFeedRepository(feeds))

    result = await searcher.execute(FeedCriteria())

    assert result == feeds


async def test_returns_nothing_when_there_are_no_feeds() -> None:
    searcher = FeedSearcher(InMemoryFeedRepository())

    assert await searcher.execute(FeedCriteria()) == []


async def test_returns_the_feeds_of_one_category_newest_first() -> None:
    older = FeedMother.random(
        category=FeedCategory.SPORTS,
        created_at=FeedCreatedAtMother.create("2026-10-18T10:00:00.000Z"),
    )
    newer = FeedMother.random(
        category=FeedCategory.SPORTS,
        created_at=FeedCreatedAtMother.create("2026-10-20T10:00:00.000Z"),
    )
    other_category = FeedMother.random(category=FeedCategory.CULTURE)
    searcher = FeedSearcher(InMemoryFeedRepository([older, other_category, newer]))

    result = await searcher.execute(
        FeedCriteria(
            filters=(Filter("category", FeedCategory.SPORTS),),
            order=Order("created_at", "desc"),
        )
    )

    assert result == [newer, older]
