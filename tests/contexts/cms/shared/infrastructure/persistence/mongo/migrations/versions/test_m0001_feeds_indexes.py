from collections.abc import Mapping

import pytest
from pymongo.errors import OperationFailure

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0001_feeds_indexes,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)

pytestmark = pytest.mark.integration

EXPECTED_INDEXES = {
    "_id_": [("_id", 1)],
    "created_at_desc": [("createdAt", -1)],
    "source_created_at_desc": [("source", 1), ("createdAt", -1)],
    "source_title_created_at": [("source", 1), ("title", 1), ("createdAt", 1)],
}


async def feeds_indexes(db: MongoDatabase) -> Mapping[str, Mapping[str, object]]:
    return await db["feeds"].index_information()


async def test_creates_the_feeds_indexes_none_of_them_unique(db: MongoDatabase) -> None:
    await m0001_feeds_indexes.up(db)

    indexes = await feeds_indexes(db)
    assert {name: index["key"] for name, index in indexes.items()} == EXPECTED_INDEXES
    assert not any(index.get("unique") for index in indexes.values())


async def test_running_it_again_succeeds_and_keeps_the_same_indexes(db: MongoDatabase) -> None:
    await m0001_feeds_indexes.up(db)
    first_run = await feeds_indexes(db)

    await m0001_feeds_indexes.up(db)

    assert await feeds_indexes(db) == first_run


async def test_fails_without_dropping_an_index_with_the_same_keys_and_another_name(
    db: MongoDatabase,
) -> None:
    await db["feeds"].create_index([("createdAt", -1)], name="created_by_hand")

    with pytest.raises(OperationFailure):
        await m0001_feeds_indexes.up(db)

    assert "created_by_hand" in await feeds_indexes(db)
