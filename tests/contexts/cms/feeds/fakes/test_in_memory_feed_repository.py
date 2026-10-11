from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_updated_at import FeedUpdatedAt
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


def _feed(source: FeedSource, created_at: str) -> Feed:
    return FeedMother.random(source=source, created_at=FeedCreatedAtMother.create(created_at))


OLDEST = _feed(FeedSource.CMS, "2026-10-01T10:00:00.000Z")
MIDDLE = _feed(FeedSource.EL_MUNDO, "2026-10-02T10:00:00.000Z")
NEWEST = _feed(FeedSource.EL_ESPANOL, "2026-10-03T10:00:00.000Z")
FEEDS = [MIDDLE, OLDEST, NEWEST]


async def test_search_without_filters_returns_every_feed_in_storage_order() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    assert await repository.search(FeedCriteria()) == FEEDS


async def test_search_combines_filters_with_or() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.CMS), Filter("source", FeedSource.EL_ESPANOL))
        )
    )

    assert found == [OLDEST, NEWEST]


async def test_search_filters_by_the_primitive_value_of_a_field() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    found = await repository.search(FeedCriteria(filters=(Filter("id", MIDDLE.id.value),)))

    assert found == [MIDDLE]


async def test_search_orders_by_a_field_in_both_directions() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    ascending = await repository.search(FeedCriteria(order=Order("created_at", "asc")))
    descending = await repository.search(FeedCriteria(order=Order("created_at", "desc")))

    assert ascending == [OLDEST, MIDDLE, NEWEST]
    assert descending == [NEWEST, MIDDLE, OLDEST]


async def test_search_orders_null_values_first_when_ascending() -> None:
    updated = FeedMother.random(updated_at=FeedUpdatedAt("2026-10-05T10:00:00.000Z"))
    not_updated = FeedMother.random(updated_at=FeedUpdatedAt(None))
    repository = InMemoryFeedRepository([updated, not_updated])

    found = await repository.search(FeedCriteria(order=Order("updated_at", "asc")))

    assert found == [not_updated, updated]


async def test_search_applies_filters_then_order_then_limit() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.EL_MUNDO), Filter("source", FeedSource.CMS)),
            order=Order("created_at", "desc"),
            limit=1,
        )
    )

    assert found == [MIDDLE]
