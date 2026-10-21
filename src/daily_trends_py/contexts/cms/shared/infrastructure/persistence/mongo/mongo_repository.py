from collections.abc import Mapping

from pymongo.errors import DuplicateKeyError

from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
    MongoDocument,
)


class MongoRepository:
    def __init__(self, client: MongoClient, collection_name: str) -> None:
        self._collection: MongoCollection = client.get_default_database()[collection_name]

    async def _insert(self, document: MongoDocument, unique_key: str = "_id") -> bool:
        """Insert a new document; `False` when one with the same `unique_key` already exists.

        A duplicate on any other unique index is still raised.
        """
        try:
            await self._collection.insert_one(document)
        except DuplicateKeyError as error:
            if (error.details or {}).get("keyPattern") != {unique_key: 1}:
                raise
            return False
        return True

    async def _update(self, document: MongoDocument) -> bool:
        """Set the fields of an existing document; `False` when there is none with its `_id`."""
        result = await self._collection.update_one({"_id": document["_id"]}, {"$set": document})
        return result.matched_count == 1

    async def _by_id(self, id: str) -> MongoDocument | None:
        return await self._collection.find_one({"_id": id})

    async def _find_one(self, query: MongoDocument) -> MongoDocument | None:
        return await self._collection.find_one(query)

    async def _by_criteria(
        self, criteria: Criteria, storage_fields: Mapping[str, str]
    ) -> list[MongoDocument]:
        """Search by `criteria`; `storage_fields` renames domain fields that are stored apart."""

        def stored(field: str) -> str:
            return storage_fields.get(field, field)

        query: MongoDocument = {}
        if criteria.filters:
            query["$or"] = [{stored(f.field): f.value} for f in criteria.filters]
        sort = (
            None
            if criteria.order is None
            else [(stored(criteria.order.field), 1 if criteria.order.direction == "asc" else -1)]
        )
        # pymongo reads a limit of 0 as no limit.
        cursor = self._collection.find(query, sort=sort, limit=criteria.limit or 0)
        return [document async for document in cursor]

    async def _exists(self, query: MongoDocument) -> bool:
        return await self._collection.find_one(query, projection={"_id": 1}) is not None

    async def _remove(self, id: str) -> None:
        await self._collection.delete_one({"_id": id})
