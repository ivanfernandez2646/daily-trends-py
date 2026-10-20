from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from pymongo.errors import DuplicateKeyError

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
    async def create(self, document: MongoDocument) -> bool:
        return await self._insert(document)

    async def update(self, document: MongoDocument) -> bool:
        return await self._update(document)

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


async def test_insert_stores_the_document_as_given(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())

    inserted = await repository.create({"_id": id, "title": "A title", "description": None})

    assert inserted
    assert await collection.find_one({"_id": id}) == {
        "_id": id,
        "title": "A title",
        "description": None,
    }


async def test_insert_on_an_existing_id_returns_false_and_keeps_the_original_document(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())
    await repository.create({"_id": id, "title": "A title"})

    inserted = await repository.create({"_id": id, "title": "Another title"})

    assert not inserted
    assert await collection.find_one({"_id": id}) == {"_id": id, "title": "A title"}


async def test_insert_raises_a_duplicate_key_on_another_unique_index(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    await collection.create_index("slug", unique=True)
    first, second = str(uuid4()), str(uuid4())
    await repository.create({"_id": first, "slug": "same"})

    with pytest.raises(DuplicateKeyError):
        await repository.create({"_id": second, "slug": "same"})


async def test_update_sets_the_sent_fields_keeping_the_others(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())
    await repository.create({"_id": id, "title": "A title", "author": "An author"})

    updated = await repository.update({"_id": id, "title": "Another title"})

    assert updated
    assert await collection.find_one({"_id": id}) == {
        "_id": id,
        "title": "Another title",
        "author": "An author",
    }


async def test_update_on_a_missing_id_returns_false_and_inserts_nothing(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())

    updated = await repository.update({"_id": id, "title": "A title"})

    assert not updated
    assert await collection.count_documents({}) == 0


async def test_by_id_returns_the_stored_document(
    repository: ThingMongoRepository,
) -> None:
    id = str(uuid4())
    await repository.create({"_id": id, "title": "A title"})

    document = await repository.search(id)

    assert document == {"_id": id, "title": "A title"}


async def test_by_id_returns_none_when_document_does_not_exist(
    repository: ThingMongoRepository,
) -> None:
    assert await repository.search(str(uuid4())) is None


async def test_remove_deletes_document(
    repository: ThingMongoRepository, collection: MongoCollection
) -> None:
    id = str(uuid4())
    await repository.create({"_id": id, "title": "A title"})

    await repository.delete(id)

    assert await collection.find_one({"_id": id}) is None


async def test_remove_ignores_missing_document(repository: ThingMongoRepository) -> None:
    await repository.delete(str(uuid4()))
