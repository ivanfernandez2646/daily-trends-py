from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pymongo.errors import ServerSelectionTimeoutError

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
    create_mongo_client,
)


@pytest.mark.integration
async def test_returns_a_connected_client(mongo_client: MongoClient) -> None:
    result = await mongo_client.admin.command("ping")

    assert result["ok"] == 1


@pytest.fixture
async def collection(mongo_client: MongoClient) -> AsyncIterator[MongoCollection]:
    collection = mongo_client.get_default_database()[f"dates-{uuid4()}"]
    yield collection
    await collection.drop()


@pytest.mark.integration
async def test_reads_stored_dates_back_as_aware_utc_datetimes(collection: MongoCollection) -> None:
    stored = datetime(2026, 10, 9, 10, 0, 0, 123_000, tzinfo=timezone(timedelta(hours=2)))
    await collection.insert_one({"_id": "a", "at": stored})

    document = await collection.find_one({"_id": "a"})

    assert document is not None
    assert document["at"] == stored
    assert isinstance(document["at"], datetime)
    assert document["at"].tzinfo is UTC


async def test_fails_when_mongo_is_unreachable() -> None:
    with pytest.raises(ServerSelectionTimeoutError):
        await create_mongo_client("mongodb://localhost:1/daily-trends?serverSelectionTimeoutMS=100")
