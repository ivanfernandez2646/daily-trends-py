import pytest

from daily_trends_py.contexts.cms.feeds.domain.errors import FeedAlreadyExists, FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_description_mother import FeedDescriptionMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.domain.feed_title_mother import FeedTitleMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository


def _feed(source: FeedSource, created_at: str) -> Feed:
    return FeedMother.random(source=source, created_at=FeedCreatedAtMother.create(created_at))


OLDEST = _feed(FeedSource.CMS, "2026-10-01T10:00:00.000Z")
MIDDLE = _feed(FeedSource.EL_MUNDO, "2026-10-02T10:00:00.000Z")
NEWEST = _feed(FeedSource.EL_ESPANOL, "2026-10-03T10:00:00.000Z")
FEEDS = [MIDDLE, OLDEST, NEWEST]


async def test_create_on_an_existing_id_raises_and_keeps_the_stored_feed() -> None:
    stored = FeedMother.random()
    repository = InMemoryFeedRepository([stored])
    same_id = FeedMother.random(id=stored.id)

    with pytest.raises(FeedAlreadyExists):
        await repository.create(same_id)

    assert await repository.find(stored.id) is stored
    assert repository.created == []


async def test_update_on_a_missing_id_raises_and_stores_nothing() -> None:
    repository = InMemoryFeedRepository()
    missing = FeedMother.random()

    with pytest.raises(FeedNotFound):
        await repository.update(missing)

    assert await repository.find(missing.id) is None
    assert repository.updated == []


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


async def test_search_combines_filters_on_different_fields_with_and() -> None:
    cms_sports = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.SPORTS)
    cms_culture = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.CULTURE)
    el_mundo_sports = FeedMother.random(source=FeedSource.EL_MUNDO, category=FeedCategory.SPORTS)
    repository = InMemoryFeedRepository([cms_sports, cms_culture, el_mundo_sports])

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.CMS), Filter("category", FeedCategory.SPORTS))
        )
    )

    assert found == [cms_sports]


async def test_search_ors_filters_on_the_same_field_and_ands_them_with_other_fields() -> None:
    cms_sports = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.SPORTS)
    cms_culture = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.CULTURE)
    el_mundo_sports = FeedMother.random(source=FeedSource.EL_MUNDO, category=FeedCategory.SPORTS)
    el_pais_sports = FeedMother.random(source=FeedSource.EL_PAIS, category=FeedCategory.SPORTS)
    repository = InMemoryFeedRepository([cms_sports, cms_culture, el_mundo_sports, el_pais_sports])

    found = await repository.search(
        FeedCriteria(
            filters=(
                Filter("source", FeedSource.CMS),
                Filter("category", FeedCategory.SPORTS),
                Filter("source", FeedSource.EL_MUNDO),
            )
        )
    )

    assert found == [cms_sports, el_mundo_sports]


async def test_search_filters_by_the_primitive_value_of_a_field() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    found = await repository.search(FeedCriteria(filters=(Filter("id", MIDDLE.id.value),)))

    assert found == [MIDDLE]


async def test_search_orders_by_a_field_in_both_directions() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    ascending = await repository.search(FeedCriteria(orders=(Order("created_at", "asc"),)))
    descending = await repository.search(FeedCriteria(orders=(Order("created_at", "desc"),)))

    assert ascending == [OLDEST, MIDDLE, NEWEST]
    assert descending == [NEWEST, MIDDLE, OLDEST]


async def test_search_orders_null_values_first_when_ascending() -> None:
    updated = FeedMother.random(updated_at=FeedUpdatedAtMother.create("2026-10-05T10:00:00.000Z"))
    not_updated = FeedMother.random(updated_at=FeedUpdatedAtMother.create(None))
    repository = InMemoryFeedRepository([updated, not_updated])

    found = await repository.search(FeedCriteria(orders=(Order("updated_at", "asc"),)))

    assert found == [not_updated, updated]


async def test_search_applies_filters_then_order_then_limit() -> None:
    repository = InMemoryFeedRepository(FEEDS)

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.EL_MUNDO), Filter("source", FeedSource.CMS)),
            orders=(Order("created_at", "desc"),),
            limit=1,
        )
    )

    assert found == [MIDDLE]


def _batch(created_at: str, *ids: str) -> list[Feed]:
    return [
        FeedMother.random(
            id=FeedIdMother.create(id), created_at=FeedCreatedAtMother.create(created_at)
        )
        for id in ids
    ]


EARLIER_BATCH = _batch(
    "2026-10-20T08:00:00.000Z",
    "11111111-1111-4111-8111-111111111111",
    "33333333-3333-4333-8333-333333333333",
)
LATER_BATCH = _batch(
    "2026-10-20T10:00:00.000Z",
    "22222222-2222-4222-8222-222222222222",
    "44444444-4444-4444-8444-444444444444",
)


async def test_search_in_the_list_order_breaks_ties_on_the_creation_date_by_id() -> None:
    repository = InMemoryFeedRepository([*EARLIER_BATCH, *LATER_BATCH])

    found = await repository.search(FeedCriteria(orders=FeedCriteria.LIST_ORDER))

    assert found == [LATER_BATCH[1], LATER_BATCH[0], EARLIER_BATCH[1], EARLIER_BATCH[0]]


async def test_search_starts_strictly_after_the_position() -> None:
    repository = InMemoryFeedRepository([*EARLIER_BATCH, *LATER_BATCH])
    position = LATER_BATCH[0]

    found = await repository.search(
        FeedCriteria(
            orders=FeedCriteria.LIST_ORDER,
            after=(position.created_at.value, position.id.value),
        )
    )

    assert found == [EARLIER_BATCH[1], EARLIER_BATCH[0]]


async def test_search_starts_after_the_position_of_a_deleted_feed() -> None:
    repository = InMemoryFeedRepository([*EARLIER_BATCH, *LATER_BATCH])
    position = LATER_BATCH[0]
    await repository.delete(position)

    found = await repository.search(
        FeedCriteria(
            orders=FeedCriteria.LIST_ORDER,
            after=(position.created_at.value, position.id.value),
        )
    )

    assert found == [EARLIER_BATCH[1], EARLIER_BATCH[0]]


def _headline(title: str, description: str | None = None) -> Feed:
    return FeedMother.random(
        title=FeedTitleMother.create(title),
        description=FeedDescriptionMother.create(description),
    )


async def _search_text(repository: InMemoryFeedRepository, text: str) -> list[Feed]:
    return await repository.search(FeedCriteria(orders=FeedCriteria.LIST_ORDER, text=text))


async def test_search_finds_a_whole_word_ignoring_case_and_accents() -> None:
    football = _headline("Fútbol: el Madrid gana")
    repository = InMemoryFeedRepository([football, _headline("Elecciones generales")])

    assert await _search_text(repository, "futbol") == [football]
    assert await _search_text(repository, "MADRID") == [football]


async def test_search_does_not_match_a_fragment_of_a_word() -> None:
    repository = InMemoryFeedRepository([_headline("Fútbol: el Madrid gana")])

    assert await _search_text(repository, "fut") == []


async def test_search_finds_the_words_in_the_description() -> None:
    feed = _headline("Última hora", "Lluvias en Barcelona")
    repository = InMemoryFeedRepository([feed, _headline("Última hora", None)])

    assert await _search_text(repository, "barcelona") == [feed]


async def test_search_finds_feeds_with_any_of_the_words() -> None:
    madrid = _headline("Madrid", None)
    barcelona = _headline("Barcelona", None)
    repository = InMemoryFeedRepository([madrid, barcelona, _headline("Sevilla", None)])

    found = await _search_text(repository, "madrid barcelona")

    assert {feed.id for feed in found} == {madrid.id, barcelona.id}


async def test_search_ands_the_text_with_the_filters() -> None:
    cms = FeedMother.random(source=FeedSource.CMS, title=FeedTitleMother.create("Madrid"))
    el_mundo = FeedMother.random(source=FeedSource.EL_MUNDO, title=FeedTitleMother.create("Madrid"))
    cms_sevilla = FeedMother.random(
        source=FeedSource.CMS,
        title=FeedTitleMother.create("Sevilla"),
        description=FeedDescriptionMother.create(None),
    )
    repository = InMemoryFeedRepository([cms, el_mundo, cms_sevilla])

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.CMS),),
            orders=FeedCriteria.LIST_ORDER,
            text="madrid",
        )
    )

    assert found == [cms]
