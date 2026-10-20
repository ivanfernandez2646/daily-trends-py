from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_already_exists import FeedAlreadyExists
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.feeds.domain.feed_updated_at import FeedUpdatedAt
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.invalid_stored_feed import (  # noqa: E501
    InvalidStoredFeed,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
)
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother

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
    feed = FeedMother.random()

    await repository.create(feed)

    found = await repository.find(feed.id)
    assert found is not None
    assert found.to_primitives() == feed.to_primitives()


async def test_stores_the_feed_document_under_its_id_keeping_nulls(
    repository: MongoFeedRepository, collection: MongoCollection
) -> None:
    feed = FeedMother.random(description=FeedDescription(None), updated_at=FeedUpdatedAt(None))

    await repository.create(feed)

    primitives = feed.to_primitives()
    assert await collection.find_one({"_id": feed.id.value}) == {
        "_id": feed.id.value,
        "title": primitives["title"],
        "description": None,
        "author": primitives["author"],
        "source": primitives["source"].value,
        "createdAt": primitives["createdAt"],
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


async def _insert_with_created_at(collection: MongoCollection, created_at: object) -> str:
    primitives = FeedMother.random().to_primitives()
    document: dict[str, object] = {k: v for k, v in primitives.items() if k != "id"}
    document["_id"] = primitives["id"]
    if created_at is _MISSING:
        del document["createdAt"]
    else:
        document["createdAt"] = created_at
    await collection.insert_one(document)
    return primitives["id"]


_MISSING = object()


@pytest.fixture
async def malformed_feed_id(collection: MongoCollection) -> str:
    return await _insert_with_created_at(collection, "not-a-date")


async def test_find_raises_when_the_stored_feed_is_invalid(
    repository: MongoFeedRepository, malformed_feed_id: str
) -> None:
    with pytest.raises(InvalidStoredFeed) as error:
        await repository.find(FeedIdMother.create(malformed_feed_id))

    assert str(error.value) == (
        f"Stored feed <{malformed_feed_id}> is invalid: "
        "<FeedCreatedAt> does not allow the value <not-a-date>"
    )


@pytest.mark.parametrize(
    ("created_at", "rendered"),
    [
        pytest.param("2026-10-09T08:00:00.000Z", "2026-10-09T08:00:00.000Z", id="ISO string"),
        pytest.param(1_760_000_000_000, "1760000000000", id="number"),
        pytest.param(_MISSING, "None", id="missing"),
    ],
)
async def test_find_raises_when_the_stored_created_at_is_not_a_date(
    repository: MongoFeedRepository, collection: MongoCollection, created_at: object, rendered: str
) -> None:
    id = await _insert_with_created_at(collection, created_at)

    with pytest.raises(InvalidStoredFeed) as error:
        await repository.find(FeedIdMother.create(id))

    assert str(error.value) == (
        f"Stored feed <{id}> is invalid: <FeedCreatedAt> does not allow the value <{rendered}>"
    )


async def test_search_raises_when_a_stored_feed_is_invalid(
    repository: MongoFeedRepository, malformed_feed_id: str
) -> None:
    await repository.create(FeedMother.random())

    with pytest.raises(InvalidStoredFeed, match=f"Stored feed <{malformed_feed_id}> is invalid"):
        await repository.search(FeedCriteria())


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


async def test_search_sorts_feeds_by_creation_date_descending(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(order=Order("created_at", "desc")))

    assert _ids(found) == _ids(_newest_first(stored_feeds))


async def test_search_sorts_feeds_by_creation_date_ascending(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(order=Order("created_at", "asc")))

    assert _ids(found) == _ids(_newest_first(stored_feeds)[::-1])


async def test_search_limits_the_number_of_feeds(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(order=Order("created_at", "desc"), limit=2))

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

    found = await repository.search(FeedCriteria(order=Order("created_at", "desc")))

    assert _ids(found) == [later.id.value, earlier.id.value]


async def test_search_does_not_limit_feeds_without_a_limit(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(FeedCriteria(order=Order("created_at", "desc")))

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
