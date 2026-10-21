from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from daily_trends_py.contexts.cms.feeds.domain.errors import FeedAlreadyExists, FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedCategory,
    FeedDescription,
    FeedSource,
    FeedTitle,
    FeedUpdatedAt,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.invalid_stored_feed import (  # noqa: E501
    InvalidStoredFeed,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0005_feeds_text_index,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
)
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_description_mother import FeedDescriptionMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.domain.feed_title_mother import FeedTitleMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother
from tests.contexts.cms.feeds.domain.feed_url_mother import FeedUrlMother
from tests.contexts.cms.feeds.infrastructure.persistence.mongo.feed_document_mother import (
    MISSING,
    FeedDocumentMother,
)

DAY_START = datetime(2026, 10, 8, tzinfo=UTC)
DAY_END = datetime(2026, 10, 9, tzinfo=UTC)

pytestmark = pytest.mark.integration


@pytest.fixture
async def collection(mongo_client: MongoClient) -> AsyncIterator[MongoCollection]:
    collection = mongo_client.get_default_database()["feeds"]
    await collection.delete_many({})
    yield collection
    await collection.delete_many({})


@pytest.fixture
def repository(mongo_client: MongoClient, collection: MongoCollection) -> MongoFeedRepository:
    return MongoFeedRepository(mongo_client)


async def test_creates_a_feed_that_can_be_found_by_id(repository: MongoFeedRepository) -> None:
    feed = FeedMother.random(url=FeedUrlMother.create("https://www.elmundo.es/deportes/1.html"))

    await repository.create(feed)

    found = await repository.find(feed.id)
    assert found is not None
    assert found.to_primitives() == feed.to_primitives()


async def test_stores_the_feed_document_under_its_id_keeping_nulls(
    repository: MongoFeedRepository, collection: MongoCollection
) -> None:
    feed = FeedMother.random(
        description=FeedDescription(None),
        url=FeedUrlMother.create(None),
        updated_at=FeedUpdatedAt(None),
    )

    await repository.create(feed)

    primitives = feed.to_primitives()
    assert await collection.find_one({"_id": feed.id.value}) == {
        "_id": feed.id.value,
        "title": primitives["title"],
        "description": None,
        "author": primitives["author"],
        "source": primitives["source"].value,
        "category": primitives["category"].value,
        "url": None,
        "createdAt": primitives["created_at"],
        "updatedAt": None,
    }


async def test_stores_dates_as_native_utc_dates(
    repository: MongoFeedRepository, collection: MongoCollection
) -> None:
    created_at = datetime(2026, 10, 9, 10, 0, 0, 123_000, tzinfo=timezone(timedelta(hours=2)))
    updated_at = datetime(2026, 10, 10, 8, 30, tzinfo=UTC)
    feed = FeedMother.random(
        created_at=FeedCreatedAtMother.create(created_at),
        updated_at=FeedUpdatedAtMother.create(updated_at),
    )

    await repository.create(feed)

    document = await collection.find_one({"_id": feed.id.value})
    assert document is not None
    assert document["createdAt"] == datetime(2026, 10, 9, 8, 0, 0, 123_000, tzinfo=UTC)
    assert document["updatedAt"] == updated_at
    assert await collection.count_documents({"createdAt": {"$type": "date"}}) == 1


async def test_create_on_an_existing_id_raises_and_keeps_the_original_document(
    repository: MongoFeedRepository,
) -> None:
    original = FeedMother.random()
    await repository.create(original)

    with pytest.raises(FeedAlreadyExists):
        await repository.create(FeedMother.random(id=original.id))

    found = await repository.find(original.id)
    assert found is not None
    assert found.to_primitives() == original.to_primitives()


async def test_update_replaces_the_stored_feed_fields(repository: MongoFeedRepository) -> None:
    feed = FeedMother.random()
    await repository.create(feed)
    changed = FeedMother.random(id=feed.id)

    await repository.update(changed)

    found = await repository.find(feed.id)
    assert found is not None
    assert found.to_primitives() == changed.to_primitives()


async def test_update_on_a_missing_id_raises_and_inserts_nothing(
    repository: MongoFeedRepository, collection: MongoCollection
) -> None:
    with pytest.raises(FeedNotFound):
        await repository.update(FeedMother.random())

    assert await collection.count_documents({}) == 0


async def test_find_returns_none_when_the_feed_does_not_exist(
    repository: MongoFeedRepository,
) -> None:
    assert await repository.find(FeedIdMother.random()) is None


async def _insert(collection: MongoCollection, **overrides: object) -> str:
    document = FeedDocumentMother.random(**overrides)
    await collection.insert_one(document)
    return str(document["_id"])


@pytest.fixture
async def malformed_feed_id(collection: MongoCollection) -> str:
    return await _insert(collection, createdAt="not-a-date")


async def test_find_raises_when_the_stored_feed_is_invalid(
    repository: MongoFeedRepository, malformed_feed_id: str
) -> None:
    with pytest.raises(InvalidStoredFeed) as error:
        await repository.find(FeedIdMother.create(malformed_feed_id))

    assert str(error.value) == (
        f"Stored feed <{malformed_feed_id}> is invalid: "
        "<FeedCreatedAt> does not allow the value <not-a-date>"
    )


BROKEN_DOCUMENTS = [
    pytest.param(
        {"createdAt": "2026-10-09T08:00:00.000Z"},
        "<FeedCreatedAt> does not allow the value <2026-10-09T08:00:00.000Z>",
        id="ISO created at",
    ),
    pytest.param(
        {"createdAt": 1_760_000_000_000},
        "<FeedCreatedAt> does not allow the value <1760000000000>",
        id="numeric created at",
    ),
    pytest.param(
        {"createdAt": MISSING},
        "<FeedCreatedAt> does not allow the value <None>",
        id="missing created at",
    ),
    pytest.param(
        {"title": MISSING}, "<FeedTitle> does not allow the value <None>", id="missing title"
    ),
    pytest.param(
        {"author": MISSING}, "<FeedAuthor> does not allow the value <None>", id="missing author"
    ),
    pytest.param(
        {"source": MISSING}, "<FeedSource> does not allow the value <None>", id="missing source"
    ),
    pytest.param(
        {"source": "EL_PERIODICO"},
        "<FeedSource> does not allow the value <EL_PERIODICO>",
        id="unknown source",
    ),
    pytest.param(
        {"category": MISSING},
        "<FeedCategory> does not allow the value <None>",
        id="missing category",
    ),
    pytest.param(
        {"category": "WEATHER"},
        "<FeedCategory> does not allow the value <WEATHER>",
        id="unknown category",
    ),
    pytest.param(
        {"url": "/deportes/1.html"},
        "<FeedUrl> does not allow the value </deportes/1.html>",
        id="relative url",
    ),
    pytest.param({"url": 42}, "<FeedUrl> does not allow the value <42>", id="numeric url"),
    pytest.param({"title": 42}, "<FeedTitle> does not allow the value <42>", id="numeric title"),
    pytest.param(
        {"description": ["a"]},
        "<FeedDescription> does not allow the value <['a']>",
        id="list description",
    ),
]


@pytest.mark.parametrize(("overrides", "reason"), BROKEN_DOCUMENTS)
async def test_find_raises_invalid_stored_feed_for_a_broken_document(
    repository: MongoFeedRepository,
    collection: MongoCollection,
    overrides: dict[str, object],
    reason: str,
) -> None:
    id = await _insert(collection, **overrides)

    with pytest.raises(InvalidStoredFeed) as error:
        await repository.find(FeedIdMother.create(id))

    assert str(error.value) == f"Stored feed <{id}> is invalid: {reason}"


@pytest.mark.parametrize(("overrides", "reason"), BROKEN_DOCUMENTS)
async def test_search_raises_invalid_stored_feed_for_a_broken_document(
    repository: MongoFeedRepository,
    collection: MongoCollection,
    overrides: dict[str, object],
    reason: str,
) -> None:
    await repository.create(FeedMother.random())
    id = await _insert(collection, **overrides)

    with pytest.raises(InvalidStoredFeed) as error:
        await repository.search(FeedCriteria())

    assert str(error.value) == f"Stored feed <{id}> is invalid: {reason}"


async def test_find_reads_a_document_without_update_date_as_never_updated(
    repository: MongoFeedRepository, collection: MongoCollection
) -> None:
    id = await _insert(collection, updatedAt=MISSING)

    found = await repository.find(FeedIdMother.create(id))

    assert found is not None
    assert found.updated_at.value is None


async def test_delete_removes_only_the_given_feed(repository: MongoFeedRepository) -> None:
    feed, other = FeedMother.random(), FeedMother.random()
    await repository.create(feed)
    await repository.create(other)

    await repository.delete(feed)

    assert await repository.find(feed.id) is None
    assert await repository.find(other.id) is not None


@pytest.fixture
async def stored_feeds(repository: MongoFeedRepository) -> list[Feed]:
    sources = [
        FeedSource.CMS,
        FeedSource.CMS,
        FeedSource.CMS,
        FeedSource.EL_PAIS,
        FeedSource.EL_MUNDO,
    ]
    feeds = [FeedMother.random(source=source) for source in sources]
    for feed in feeds:
        await repository.create(feed)
    return feeds


def _ids(feeds: list[Feed]) -> list[str]:
    return [feed.id.value for feed in feeds]


def _newest_first(feeds: list[Feed]) -> list[Feed]:
    return sorted(feeds, key=lambda feed: feed.created_at.value, reverse=True)


async def test_search_returns_every_feed_without_filters(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria())

    assert sorted(_ids(found)) == sorted(_ids(stored_feeds))


async def test_search_returns_an_empty_list_when_there_are_no_feeds(
    repository: MongoFeedRepository,
) -> None:
    assert await repository.search(FeedCriteria()) == []


async def test_search_filters_feeds_by_a_condition(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(filters=(Filter("source", FeedSource.CMS),)))

    assert sorted(_ids(found)) == sorted(_ids(stored_feeds[:3]))


async def test_search_combines_filter_conditions_with_or(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.EL_PAIS), Filter("source", FeedSource.EL_MUNDO))
        )
    )

    assert sorted(_ids(found)) == sorted(_ids(stored_feeds[3:]))


async def test_search_combines_filters_on_different_fields_with_and(
    repository: MongoFeedRepository,
) -> None:
    cms_sports = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.SPORTS)
    cms_culture = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.CULTURE)
    el_mundo_sports = FeedMother.random(source=FeedSource.EL_MUNDO, category=FeedCategory.SPORTS)
    for feed in (cms_sports, cms_culture, el_mundo_sports):
        await repository.create(feed)

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.CMS), Filter("category", FeedCategory.SPORTS))
        )
    )

    assert _ids(found) == _ids([cms_sports])


async def test_search_ors_filters_on_the_same_field_and_ands_them_with_other_fields(
    repository: MongoFeedRepository,
) -> None:
    cms_sports = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.SPORTS)
    cms_culture = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.CULTURE)
    el_mundo_sports = FeedMother.random(source=FeedSource.EL_MUNDO, category=FeedCategory.SPORTS)
    el_pais_sports = FeedMother.random(source=FeedSource.EL_PAIS, category=FeedCategory.SPORTS)
    for feed in (cms_sports, cms_culture, el_mundo_sports, el_pais_sports):
        await repository.create(feed)

    found = await repository.search(
        FeedCriteria(
            filters=(
                Filter("source", FeedSource.CMS),
                Filter("category", FeedCategory.SPORTS),
                Filter("source", FeedSource.EL_MUNDO),
            )
        )
    )

    assert sorted(_ids(found)) == sorted(_ids([cms_sports, el_mundo_sports]))


async def test_search_sorts_feeds_by_creation_date_descending(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(orders=(Order("created_at", "desc"),)))

    assert _ids(found) == _ids(_newest_first(stored_feeds))


async def test_search_sorts_feeds_by_creation_date_ascending(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(orders=(Order("created_at", "asc"),)))

    assert _ids(found) == _ids(_newest_first(stored_feeds)[::-1])


async def test_search_limits_the_number_of_feeds(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(orders=(Order("created_at", "desc"),), limit=2))

    assert _ids(found) == _ids(_newest_first(stored_feeds)[:2])


async def test_search_sorts_creation_dates_chronologically_across_offsets(
    repository: MongoFeedRepository,
) -> None:
    # 08:00 UTC: as text it sorted after 09:30Z.
    earlier = FeedMother.random(
        created_at=FeedCreatedAtMother.create("2026-10-09T10:00:00.000+02:00")
    )
    later = FeedMother.random(created_at=FeedCreatedAtMother.create("2026-10-09T09:30:00.000Z"))
    await repository.create(earlier)
    await repository.create(later)

    found = await repository.search(FeedCriteria(orders=(Order("created_at", "desc"),)))

    assert _ids(found) == [later.id.value, earlier.id.value]


async def test_search_does_not_limit_feeds_without_a_limit(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(orders=(Order("created_at", "desc"),)))

    assert len(found) == len(stored_feeds)


async def test_search_filters_by_id_stored_as_the_mongo_id(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(filters=(Filter("id", stored_feeds[1].id.value),)))

    assert _ids(found) == [stored_feeds[1].id.value]


async def test_search_maps_documents_back_to_feeds(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(filters=(Filter("source", FeedSource.EL_PAIS),)))

    assert [feed.to_primitives() for feed in found] == [stored_feeds[3].to_primitives()]


@pytest.mark.parametrize("created_at", ["2026-10-08T00:00:00.000Z", "2026-10-08T23:59:59.999Z"])
async def test_exists_headline_finds_a_feed_with_the_same_source_and_title_that_day(
    repository: MongoFeedRepository, created_at: str
) -> None:
    await repository.create(
        FeedMother.random(
            source=FeedSource.EL_MUNDO,
            title=FeedTitle("Same headline"),
            created_at=FeedCreatedAtMother.create(created_at),
        )
    )

    assert await repository.exists_headline(
        FeedSource.EL_MUNDO, FeedTitle("Same headline"), DAY_START, DAY_END
    )


@pytest.mark.parametrize(
    ("source", "title", "created_at"),
    [
        (FeedSource.EL_ESPANOL, "Same headline", "2026-10-08T12:00:00.000Z"),
        (FeedSource.EL_MUNDO, "Another headline", "2026-10-08T12:00:00.000Z"),
        (FeedSource.EL_MUNDO, "same headline", "2026-10-08T12:00:00.000Z"),
        (FeedSource.EL_MUNDO, "Same headline", "2026-10-07T23:59:59.999Z"),
        (FeedSource.EL_MUNDO, "Same headline", "2026-10-09T00:00:00.000Z"),
    ],
)
async def test_exists_headline_ignores_another_source_title_or_day(
    repository: MongoFeedRepository, source: FeedSource, title: str, created_at: str
) -> None:
    await repository.create(
        FeedMother.random(
            source=source,
            title=FeedTitle(title),
            created_at=FeedCreatedAtMother.create(created_at),
        )
    )

    assert not await repository.exists_headline(
        FeedSource.EL_MUNDO, FeedTitle("Same headline"), DAY_START, DAY_END
    )


@pytest.mark.parametrize(
    ("created_at", "exists"),
    [
        pytest.param("2026-10-07T22:00:00.000Z", True, id="at since"),
        pytest.param("2026-10-08T21:59:59.999Z", True, id="just before until"),
        pytest.param("2026-10-08T22:00:00.000Z", False, id="at until"),
        pytest.param("2026-10-07T21:59:59.999Z", False, id="just before since"),
    ],
)
async def test_exists_headline_compares_bounds_given_in_another_zone_with_stored_utc_dates(
    repository: MongoFeedRepository, created_at: str, exists: bool
) -> None:
    await repository.create(
        FeedMother.random(
            source=FeedSource.EL_MUNDO,
            title=FeedTitle("Same headline"),
            created_at=FeedCreatedAtMother.create(created_at),
        )
    )
    madrid = ZoneInfo("Europe/Madrid")

    found = await repository.exists_headline(
        FeedSource.EL_MUNDO,
        FeedTitle("Same headline"),
        datetime(2026, 10, 8, tzinfo=madrid),
        datetime(2026, 10, 9, tzinfo=madrid),
    )

    assert found is exists


async def test_search_returns_the_newest_feeds_of_one_source(
    repository: MongoFeedRepository,
) -> None:
    feeds = [
        FeedMother.random(
            source=source,
            created_at=FeedCreatedAtMother.create(f"2026-10-08T{hour:02}:00:00.000Z"),
        )
        for hour, source in enumerate(
            [
                FeedSource.LA_RAZON,
                FeedSource.EL_MUNDO,
                FeedSource.LA_RAZON,
                FeedSource.LA_RAZON,
                FeedSource.EL_MUNDO,
            ]
        )
    ]
    for feed in feeds:
        await repository.create(feed)

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.LA_RAZON),),
            orders=(Order("created_at", "desc"),),
            limit=2,
        )
    )

    assert _ids(found) == _ids([feeds[3], feeds[2]])


async def test_search_returns_the_feeds_of_one_category_newest_first(
    repository: MongoFeedRepository,
) -> None:
    def feed(category: FeedCategory, created_at: str) -> Feed:
        return FeedMother.random(
            category=category, created_at=FeedCreatedAtMother.create(created_at)
        )

    older = feed(FeedCategory.SPORTS, "2026-10-18T10:00:00.000Z")
    newer = feed(FeedCategory.SPORTS, "2026-10-20T10:00:00.000Z")
    other = feed(FeedCategory.CULTURE, "2026-10-19T10:00:00.000Z")
    for stored in (older, other, newer):
        await repository.create(stored)

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("category", FeedCategory.SPORTS),),
            orders=(Order("created_at", "desc"),),
        )
    )

    assert [found_feed.id for found_feed in found] == [newer.id, older.id]


def _batch(created_at: str, *ids: str) -> list[Feed]:
    return [
        FeedMother.random(
            id=FeedIdMother.create(id), created_at=FeedCreatedAtMother.create(created_at)
        )
        for id in ids
    ]


@pytest.fixture
async def batches(repository: MongoFeedRepository) -> tuple[list[Feed], list[Feed]]:
    """Two scraping runs of two feeds each, every feed of a run sharing its creation date."""
    earlier = _batch(
        "2026-10-20T08:00:00.000Z",
        "11111111-1111-4111-8111-111111111111",
        "33333333-3333-4333-8333-333333333333",
    )
    later = _batch(
        "2026-10-20T10:00:00.000Z",
        "22222222-2222-4222-8222-222222222222",
        "44444444-4444-4444-8444-444444444444",
    )
    for feed in (*earlier, *later):
        await repository.create(feed)
    return earlier, later


async def test_search_in_the_list_order_breaks_ties_on_the_creation_date_by_id(
    repository: MongoFeedRepository, batches: tuple[list[Feed], list[Feed]]
) -> None:
    earlier, later = batches

    found = await repository.search(FeedCriteria(orders=FeedCriteria.LIST_ORDER))

    assert _ids(found) == _ids([later[1], later[0], earlier[1], earlier[0]])


async def test_search_starts_strictly_after_the_position(
    repository: MongoFeedRepository, batches: tuple[list[Feed], list[Feed]]
) -> None:
    earlier, later = batches

    found = await repository.search(
        FeedCriteria(
            orders=FeedCriteria.LIST_ORDER,
            after=(later[0].created_at.value, later[0].id.value),
            limit=1,
        )
    )

    assert _ids(found) == _ids([earlier[1]])


async def test_search_starts_after_the_position_of_a_deleted_feed(
    repository: MongoFeedRepository, batches: tuple[list[Feed], list[Feed]]
) -> None:
    earlier, later = batches
    await repository.delete(later[0])

    found = await repository.search(
        FeedCriteria(
            orders=FeedCriteria.LIST_ORDER,
            after=(later[0].created_at.value, later[0].id.value),
        )
    )

    assert _ids(found) == _ids([earlier[1], earlier[0]])


async def test_search_starts_after_the_position_among_the_filtered_feeds(
    repository: MongoFeedRepository,
) -> None:
    newest, newer, other_source, older = (
        FeedMother.random(
            source=source, created_at=FeedCreatedAtMother.create(f"2026-10-2{day}T10:00:00.000Z")
        )
        for day, source in (
            (4, FeedSource.CMS),
            (3, FeedSource.CMS),
            (2, FeedSource.EL_MUNDO),
            (1, FeedSource.CMS),
        )
    )
    for feed in (newest, newer, other_source, older):
        await repository.create(feed)

    found = await repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.CMS),),
            orders=FeedCriteria.LIST_ORDER,
            after=(newest.created_at.value, newest.id.value),
        )
    )

    assert _ids(found) == _ids([newer, older])


@pytest.fixture
async def text_repository(
    repository: MongoFeedRepository, collection: MongoCollection
) -> MongoFeedRepository:
    """The repository over a collection with the text index that `?q=` needs."""
    await m0005_feeds_text_index.up(collection.database)
    return repository


async def _store_headlines(repository: MongoFeedRepository, *headlines: str) -> list[Feed]:
    """One feed per headline, a minute apart, the first one the oldest."""
    feeds = [
        FeedMother.random(
            title=FeedTitleMother.create(headline),
            description=FeedDescriptionMother.create(None),
            created_at=FeedCreatedAtMother.create(
                datetime(2026, 10, 20, tzinfo=UTC) + timedelta(minutes=minute)
            ),
        )
        for minute, headline in enumerate(headlines)
    ]
    for feed in feeds:
        await repository.create(feed)
    return feeds


async def _search_text(repository: MongoFeedRepository, text: str) -> list[Feed]:
    return await repository.search(FeedCriteria(orders=FeedCriteria.LIST_ORDER, text=text))


@pytest.mark.parametrize(
    ("text", "headline"),
    [
        pytest.param("elecciones", "La elección del nuevo alcalde", id="stem"),
        pytest.param("Sánchez", "Entrevista a sanchez", id="accents"),
        pytest.param("FÚTBOL", "El fútbol vuelve", id="case"),
    ],
)
async def test_search_finds_spanish_words_by_stem_ignoring_case_and_accents(
    text_repository: MongoFeedRepository, text: str, headline: str
) -> None:
    feed, _ = await _store_headlines(text_repository, headline, "Noticias de Sevilla")

    assert _ids(await _search_text(text_repository, text)) == _ids([feed])


@pytest.mark.parametrize(
    "text", [pytest.param("elec", id="fragment"), pytest.param("el de", id="stop words")]
)
async def test_search_finds_nothing_for_a_fragment_or_only_stop_words(
    text_repository: MongoFeedRepository, text: str
) -> None:
    await _store_headlines(text_repository, "El día de las elecciones")

    assert await _search_text(text_repository, text) == []


async def test_search_finds_the_words_in_the_description(
    text_repository: MongoFeedRepository,
) -> None:
    feed = FeedMother.random(
        title=FeedTitleMother.create("Última hora"),
        description=FeedDescriptionMother.create("Lluvias en Barcelona"),
    )
    await text_repository.create(feed)
    await _store_headlines(text_repository, "Noticias de Sevilla")

    assert _ids(await _search_text(text_repository, "barcelona")) == _ids([feed])


async def test_search_finds_feeds_with_any_of_the_words_newest_first_not_by_relevance(
    text_repository: MongoFeedRepository,
) -> None:
    both, _, madrid = await _store_headlines(
        text_repository, "Madrid y Barcelona, Madrid otra vez", "Sevilla", "Madrid"
    )

    found = await _search_text(text_repository, "madrid barcelona")

    assert _ids(found) == _ids([madrid, both])


async def test_search_ands_the_text_with_the_filters_and_the_position(
    text_repository: MongoFeedRepository,
) -> None:
    start = datetime(2026, 10, 20, tzinfo=UTC)
    oldest, cms_sevilla, el_mundo, middle, newest = (
        FeedMother.random(
            source=source,
            title=FeedTitleMother.create(title),
            description=FeedDescriptionMother.create(None),
            created_at=FeedCreatedAtMother.create(start + timedelta(minutes=minute)),
        )
        for minute, (source, title) in enumerate(
            [
                (FeedSource.CMS, "Madrid"),
                (FeedSource.CMS, "Sevilla"),
                (FeedSource.EL_MUNDO, "Madrid"),
                (FeedSource.CMS, "Madrid"),
                (FeedSource.CMS, "Madrid"),
            ]
        )
    )
    for feed in (oldest, cms_sevilla, el_mundo, middle, newest):
        await text_repository.create(feed)

    found = await text_repository.search(
        FeedCriteria(
            filters=(Filter("source", FeedSource.CMS),),
            orders=FeedCriteria.LIST_ORDER,
            after=(newest.created_at.value, newest.id.value),
            text="madrid",
        )
    )

    assert _ids(found) == _ids([middle, oldest])
