from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository

HOME_SOURCES = [
    FeedSource.EL_MUNDO,
    FeedSource.EL_ESPANOL,
    FeedSource.EL_CONFIDENCIAL,
    FeedSource.LA_RAZON,
    FeedSource.LA_VANGUARDIA,
]
POLITICS = FeedCategory.POLITICS
# Ten categories, enough for ten feeds that never reach the limit of two per category.
VARIED = [category for category in FeedCategory if category is not FeedCategory.OTHER]


def _feed(source: FeedSource, created_at: str, category: FeedCategory = POLITICS) -> Feed:
    return FeedMother.random(
        source=source, category=category, created_at=FeedCreatedAtMother.create(created_at)
    )


def _newest_first(feeds: list[Feed]) -> list[Feed]:
    return sorted(feeds, key=lambda feed: feed.created_at.value, reverse=True)


async def _search(feeds: list[Feed]) -> list[Feed]:
    return await FeedHomeSearcher(InMemoryFeedRepository(feeds)).execute()


def _three_feeds(source: FeedSource, index: int) -> list[Feed]:
    """Three feeds an hour older than those of `index - 1`; the third repeats the first category."""
    categories = (VARIED[2 * index], VARIED[2 * index + 1], VARIED[2 * index])
    return [
        _feed(source, f"2026-10-08T{10 - index:02}:{minute:02}:00.000Z", category)
        for minute, category in zip((20, 10, 0), categories, strict=True)
    ]


async def test_returns_the_two_newest_feeds_of_each_home_source_when_categories_vary() -> None:
    # El Mundo's third feed is newer than every feed of the other sources.
    feeds = {source: _three_feeds(source, index) for index, source in enumerate(HOME_SOURCES)}

    result = await _search([feed for source_feeds in feeds.values() for feed in source_feeds])

    assert result == _newest_first(
        [feed for source_feeds in feeds.values() for feed in source_feeds[:2]]
    )


async def test_picks_at_most_two_feeds_of_a_category_across_sources() -> None:
    others = [category for category in FeedCategory if category is not POLITICS]
    openings = [
        _feed(source, f"2026-10-08T12:{50 - index:02}:00.000Z")
        for index, source in enumerate(HOME_SOURCES)
    ]
    older = [
        [
            _feed(
                source,
                f"2026-10-08T{10 - rank:02}:{50 - index:02}:00.000Z",
                others[2 * index + rank],
            )
            for rank in range(2)
        ]
        for index, source in enumerate(HOME_SOURCES)
    ]

    result = await _search([*openings, *(feed for feeds in older for feed in feeds)])

    assert result == _newest_first(
        [
            *openings[:2],
            older[0][0],
            older[1][0],
            *(feed for feeds in older[2:] for feed in feeds),
        ]
    )


async def test_fills_up_to_ten_with_the_newest_when_every_feed_has_the_same_category() -> None:
    feeds = [
        _feed(source, f"2026-10-08T{10 - index:02}:{minute:02}:00.000Z")
        for index, source in enumerate(HOME_SOURCES)
        for minute in (20, 10, 0)
    ]

    result = await _search(feeds)

    assert result == _newest_first(feeds)[:10]


async def test_returns_the_ten_newest_feeds_when_only_one_source_has_feeds() -> None:
    feeds = [
        _feed(FeedSource.EL_MUNDO, f"2026-10-08T{hour:02}:00:00.000Z", VARIED[hour % 10])
        for hour in range(12)
    ]

    result = await _search(feeds)

    assert result == _newest_first(feeds)[:10]


async def test_fills_the_slots_of_sources_with_fewer_than_two_feeds_with_the_newest_others() -> (
    None
):
    el_mundo = [
        _feed(FeedSource.EL_MUNDO, f"2026-10-08T{hour:02}:00:00.000Z", VARIED[hour - 6])
        for hour in (11, 10, 9, 8, 7, 6)
    ]
    el_espanol = _feed(FeedSource.EL_ESPANOL, "2026-10-08T05:00:00.000Z", VARIED[2])
    la_razon = [
        _feed(FeedSource.LA_RAZON, f"2026-10-08T{hour:02}:00:00.000Z", VARIED[hour + 2])
        for hour in (4, 3)
    ]
    la_vanguardia = [
        _feed(FeedSource.LA_VANGUARDIA, f"2026-10-08T{hour:02}:00:00.000Z", VARIED[hour + 7])
        for hour in (2, 1)
    ]

    result = await _search([*el_mundo, el_espanol, *la_razon, *la_vanguardia])

    assert result == [*el_mundo[:5], el_espanol, *la_razon, *la_vanguardia]


async def test_returns_every_home_feed_when_there_are_fewer_than_ten() -> None:
    feeds = [
        _feed(source, f"2026-10-08T{hour:02}:00:00.000Z", VARIED[hour])
        for hour, source in enumerate([FeedSource.EL_MUNDO, *HOME_SOURCES])
    ]

    result = await _search(feeds)

    assert result == _newest_first(feeds)


async def test_keeps_the_slots_of_a_source_whose_newest_feeds_are_old() -> None:
    week_old = [
        _feed(FeedSource.LA_RAZON, f"2026-10-01T{hour:02}:00:00.000Z", VARIED[hour])
        for hour in (9, 8)
    ]
    recent_sources = [source for source in HOME_SOURCES if source != FeedSource.LA_RAZON]
    recent = {source: _three_feeds(source, index) for index, source in enumerate(recent_sources)}

    result = await _search(
        [*week_old, *(feed for source_feeds in recent.values() for feed in source_feeds)]
    )

    assert result == _newest_first(
        [*week_old, *(feed for source_feeds in recent.values() for feed in source_feeds[:2])]
    )


async def test_takes_the_fifteen_newest_feeds_of_each_home_source_as_candidates() -> None:
    repository = InMemoryFeedRepository([])

    await FeedHomeSearcher(repository).execute()

    assert repository.searched_criteria == [
        FeedCriteria(
            filters=(Filter("source", source),),
            orders=(Order("created_at", "desc"),),
            limit=15,
        )
        for source in HOME_SOURCES
    ]


async def test_never_returns_cms_or_el_pais_feeds() -> None:
    home_feed = _feed(FeedSource.EL_MUNDO, "2026-10-08T08:00:00.000Z")
    excluded = [
        _feed(source, "2026-10-08T11:00:00.000Z") for source in (FeedSource.CMS, FeedSource.EL_PAIS)
    ]

    result = await _search([*excluded, home_feed])

    assert result == [home_feed]


async def test_answers_a_stale_front_page_as_it_is() -> None:
    stale = [
        _feed(FeedSource.EL_MUNDO, "2023-06-17T14:58:39.733Z"),
        _feed(FeedSource.LA_RAZON, "2023-06-16T14:58:39.733Z"),
    ]

    result = await _search(stale)

    assert result == stale


async def test_returns_nothing_when_there_are_no_feeds() -> None:
    assert await _search([]) == []
