from collections.abc import AsyncIterator

import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_updated_at import FeedUpdatedAt
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.invalid_stored_feed import (  # noqa: E501
    InvalidStoredFeed,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
)
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother

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


async def test_saves_a_feed_that_can_be_found_by_id(repository: MongoFeedRepository) -> None:
    feed = FeedMother.random()

    await repository.save(feed)

    found = await repository.find(feed.id)
    assert found is not None
    assert found.to_primitives() == feed.to_primitives()


async def test_stores_the_feed_document_under_its_id_keeping_nulls(
    repository: MongoFeedRepository, collection: MongoCollection
) -> None:
    feed = FeedMother.random(description=FeedDescription(None), updated_at=FeedUpdatedAt(None))

    await repository.save(feed)

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


async def test_find_returns_none_when_the_feed_does_not_exist(
    repository: MongoFeedRepository,
) -> None:
    assert await repository.find(FeedIdMother.random()) is None


@pytest.fixture
async def malformed_feed_id(collection: MongoCollection) -> str:
    primitives = FeedMother.random().to_primitives()
    await collection.insert_one(
        {
            **{k: v for k, v in primitives.items() if k != "id"},
            "_id": primitives["id"],
            "createdAt": "not-a-date",
        }
    )
    return primitives["id"]


async def test_find_raises_when_the_stored_feed_is_invalid(
    repository: MongoFeedRepository, malformed_feed_id: str
) -> None:
    with pytest.raises(InvalidStoredFeed) as error:
        await repository.find(FeedIdMother.create(malformed_feed_id))

    assert str(error.value) == (
        f"Stored feed <{malformed_feed_id}> is invalid: "
        "<FeedCreatedAt> does not allow the value <not-a-date>"
    )


async def test_search_raises_when_a_stored_feed_is_invalid(
    repository: MongoFeedRepository, malformed_feed_id: str
) -> None:
    await repository.save(FeedMother.random())

    with pytest.raises(InvalidStoredFeed, match=f"Stored feed <{malformed_feed_id}> is invalid"):
        await repository.search()


async def test_delete_removes_only_the_given_feed(repository: MongoFeedRepository) -> None:
    feed, other = FeedMother.random(), FeedMother.random()
    await repository.save(feed)
    await repository.save(other)

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
        await repository.save(feed)
    return feeds


def _ids(feeds: list[Feed]) -> list[str]:
    return [feed.id.value for feed in feeds]


def _newest_first(feeds: list[Feed]) -> list[Feed]:
    return sorted(feeds, key=lambda feed: feed.created_at.value, reverse=True)


async def test_search_returns_every_feed_without_criteria(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search()

    assert sorted(_ids(found)) == sorted(_ids(stored_feeds))


async def test_search_returns_an_empty_list_when_there_are_no_feeds(
    repository: MongoFeedRepository,
) -> None:
    assert await repository.search({}) == []


async def test_search_filters_feeds_by_a_condition(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search({"filter": [{"source": FeedSource.CMS}]})

    assert sorted(_ids(found)) == sorted(_ids(stored_feeds[:3]))


async def test_search_combines_filter_conditions_with_or(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search(
        {"filter": [{"source": FeedSource.EL_PAIS}, {"source": FeedSource.EL_MUNDO}]}
    )

    assert sorted(_ids(found)) == sorted(_ids(stored_feeds[3:]))


async def test_search_sorts_feeds_by_creation_date_descending(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search({"sort": {"createdAt": "desc"}})

    assert _ids(found) == _ids(_newest_first(stored_feeds))


async def test_search_sorts_feeds_by_creation_date_ascending(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search({"sort": {"createdAt": "asc"}})

    assert _ids(found) == _ids(_newest_first(stored_feeds)[::-1])


async def test_search_limits_the_number_of_feeds(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search({"sort": {"createdAt": "desc"}, "limit": 2})

    assert _ids(found) == _ids(_newest_first(stored_feeds)[:2])


async def test_search_does_not_limit_feeds_when_the_limit_is_zero(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search({"limit": 0})

    assert len(found) == len(stored_feeds)


async def test_search_maps_documents_back_to_feeds(
    repository: MongoFeedRepository, stored_feeds: list[Feed]
) -> None:
    found = await repository.search({"filter": [{"source": FeedSource.EL_PAIS}]})

    assert [feed.to_primitives() for feed in found] == [stored_feeds[3].to_primitives()]
