from collections.abc import Mapping

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
    MongoDocument,
)


class MongoRepository:
    def __init__(self, client: MongoClient, collection_name: str) -> None:
        self._collection: MongoCollection = client.get_default_database()[collection_name]

    async def _persist(self, id: str, primitives: Mapping[str, object]) -> None:
        document = {key: value for key, value in primitives.items() if key != "id"}
        document["_id"] = id
        await self._collection.update_one({"_id": id}, {"$set": document}, upsert=True)

    async def _by_id(self, id: str) -> MongoDocument | None:
        document = await self._collection.find_one({"_id": id})
        if document is None:
            return None
        return {**document, "id": document["_id"]}

    async def _remove(self, id: str) -> None:
        await self._collection.delete_one({"_id": id})
