from collections.abc import AsyncIterator, Mapping
from uuid import uuid4

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
    MongoDocument,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_repository import (
    MongoRepository,
)

pytestmark = pytest.mark.integration


class ThingMongoRepository(MongoRepository):
    async def save(self, id: str, primitives: Mapping[str, object]) -> None:
        await self._persist(id, primitives)

    async def search(self, id: str) -> MongoDocument | None:
        return await self._by_id(id)

    async def delete(self, id: str) -> None:
        await self._remove(id)


@pytest.fixture
async def collection(mongo_client: MongoClient) -> AsyncIterator[MongoCollection]:
    collection = mongo_client.get_default_database()[f"things-{uuid4()}"]
    yield collection
    await collection.drop()


@pytest.fixture
def repository(mongo_client: MongoClient, collection: MongoCollection) -> ThingMongoRepository:
    return ThingMongoRepository(mongo_client, collection.name)


async def test_persist_stores_document_under_id_without_id_field(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())

    await repository.save(id, {"id": id, "title": "A title", "description": None})

    assert await collection.find_one({"_id": id}) == {
        "_id": id,
        "title": "A title",
        "description": None,
    }


async def test_persist_updates_existing_document_keeping_unsent_fields(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())
    await repository.save(id, {"id": id, "title": "A title", "author": "An author"})

    await repository.save(id, {"id": id, "title": "Another title"})

    assert await collection.find_one({"_id": id}) == {
        "_id": id,
        "title": "Another title",
        "author": "An author",
    }


async def test_by_id_returns_document_with_id_copied_from_mongo_id(
    repository: ThingMongoRepository,
) -> None:
    id = str(uuid4())
    await repository.save(id, {"id": id, "title": "A title"})

    document = await repository.search(id)

    assert document == {"_id": id, "id": id, "title": "A title"}


async def test_by_id_returns_none_when_document_does_not_exist(
    repository: ThingMongoRepository,
) -> None:
    assert await repository.search(str(uuid4())) is None


async def test_remove_deletes_document(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())
    await repository.save(id, {"id": id, "title": "A title"})

    await repository.delete(id)

    assert await collection.find_one({"_id": id}) is None


async def test_remove_ignores_missing_document(repository: ThingMongoRepository) -> None:
    await repository.delete(str(uuid4()))
