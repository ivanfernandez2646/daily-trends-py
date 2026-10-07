from collections.abc import AsyncIterator

import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    DateTimeValueObject,
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
    feed = FeedMother.random(
        description=FeedDescription(None), updated_at=DateTimeValueObject(None)
    )

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
