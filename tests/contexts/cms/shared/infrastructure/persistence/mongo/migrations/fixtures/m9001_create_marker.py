from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)


async def up(db: MongoDatabase) -> None:
    await db["markers"].update_one({"_id": "m9001"}, {"$set": {}}, upsert=True)
