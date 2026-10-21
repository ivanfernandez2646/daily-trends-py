from datetime import UTC, datetime, timedelta

import pytest

from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import (
    FeedPage,
    FeedSearcher,
)
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_position import FeedPosition
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository

START = datetime(2026, 10, 1, tzinfo=UTC)


def _feeds(
    count: int,
    *,
    start: datetime = START,
    category: FeedCategory | None = None,
    source: FeedSource | None = None,
) -> list[Feed]:
    """`count` feeds one minute apart from `start`, the oldest first."""
    return [
        FeedMother.random(
            created_at=FeedCreatedAtMother.create(start + timedelta(minutes=minute)),
            category=category,
            source=source,
        )
        for minute in range(count)
    ]


def _newest_first(feeds: list[Feed]) -> list[Feed]:
    return sorted(feeds, key=lambda feed: (feed.created_at.value, feed.id.value), reverse=True)


async def _every_page(searcher: FeedSearcher, limit: int) -> list[FeedPage]:
    pages = [await searcher.execute(limit=limit)]
    while (after := pages[-1].next) is not None:
        pages.append(await searcher.execute(limit=limit, after=after))
    return pages


async def test_answers_the_feeds_in_pages_newest_first() -> None:
    feeds = _feeds(45)
    searcher = FeedSearcher(InMemoryFeedRepository(feeds))

    pages = await _every_page(searcher, limit=20)

    assert [len(page.feeds) for page in pages] == [20, 20, 5]
    assert [feed for page in pages for feed in page.feeds] == _newest_first(feeds)
    assert [page.next is None for page in pages] == [False, False, True]


async def test_a_full_last_page_has_no_next_position() -> None:
    searcher = FeedSearcher(InMemoryFeedRepository(_feeds(40)))

    pages = await _every_page(searcher, limit=20)

    assert [len(page.feeds) for page in pages] == [20, 20]
    assert pages[-1].next is None


async def test_the_next_position_is_the_last_feed_of_the_page() -> None:
    feeds = _feeds(3)
    searcher = FeedSearcher(InMemoryFeedRepository(feeds))

    page = await searcher.execute(limit=2)

    assert page.next == FeedPosition.of(feeds[1])


async def test_breaks_ties_on_the_creation_date_by_id_without_repeating_or_skipping() -> None:
    batch = [FeedMother.random(created_at=FeedCreatedAtMother.create(START)) for _ in range(5)]
    searcher = FeedSearcher(InMemoryFeedRepository(batch))

    pages = await _every_page(searcher, limit=2)

    assert [len(page.feeds) for page in pages] == [2, 2, 1]
    assert [feed for page in pages for feed in page.feeds] == sorted(
        batch, key=lambda feed: feed.id.value, reverse=True
    )


async def test_feeds_saved_between_two_pages_do_not_shift_the_next_one() -> None:
    feeds = _feeds(45)
    repository = InMemoryFeedRepository(feeds)
    searcher = FeedSearcher(repository)
    first = await searcher.execute(limit=20)
    second = await searcher.execute(limit=20, after=first.next)
    for feed in _feeds(25, start=START + timedelta(days=1)):
        await repository.create(feed)

    third = await searcher.execute(limit=20, after=second.next)

    assert third.feeds == _newest_first(feeds)[40:]
    assert third.next is None


async def test_answers_an_empty_last_page_when_there_are_no_feeds() -> None:
    searcher = FeedSearcher(InMemoryFeedRepository())

    assert await searcher.execute(limit=20) == FeedPage(feeds=[], next=None)


async def test_asks_for_one_more_feed_than_the_limit_in_the_list_order() -> None:
    repository = InMemoryFeedRepository()
    searcher = FeedSearcher(repository)

    await searcher.execute(limit=20)

    assert repository.searched_criteria == [FeedCriteria(orders=FeedCriteria.LIST_ORDER, limit=21)]


async def test_answers_only_the_feeds_of_the_category_and_the_source() -> None:
    wanted = _feeds(3, category=FeedCategory.SPORTS, source=FeedSource.EL_MUNDO)
    other_category = _feeds(2, category=FeedCategory.CULTURE, source=FeedSource.EL_MUNDO)
    other_source = _feeds(2, category=FeedCategory.SPORTS, source=FeedSource.CMS)
    searcher = FeedSearcher(InMemoryFeedRepository([*other_category, *wanted, *other_source]))

    first = await searcher.execute(
        limit=2, category=FeedCategory.SPORTS, source=FeedSource.EL_MUNDO
    )
    second = await searcher.execute(
        limit=2, after=first.next, category=FeedCategory.SPORTS, source=FeedSource.EL_MUNDO
    )

    assert [*first.feeds, *second.feeds] == _newest_first(wanted)
    assert second.next is None


@pytest.mark.parametrize("limit", [0, -1])
async def test_rejects_a_limit_that_is_not_positive(limit: int) -> None:
    searcher = FeedSearcher(InMemoryFeedRepository())

    with pytest.raises(ValueError) as error:
        await searcher.execute(limit=limit)

    assert str(error.value) == f"<FeedSearcher> does not allow the limit <{limit}>"
