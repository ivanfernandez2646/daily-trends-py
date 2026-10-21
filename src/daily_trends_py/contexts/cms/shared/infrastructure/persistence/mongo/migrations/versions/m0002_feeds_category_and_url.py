from pymongo import ASCENDING, DESCENDING, IndexModel

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)


async def up(db: MongoDatabase) -> None:
    feeds = db["feeds"]
    # Feeds stored before categories existed: none was ever classified, and none kept its link.
    await feeds.update_many({"category": {"$exists": False}}, {"$set": {"category": "OTHER"}})
    await feeds.update_many({"url": {"$exists": False}}, {"$set": {"url": None}})
    await feeds.create_indexes(
        [
            # /feed/list?category=: the newest feeds of one category.
            IndexModel(
                [("category", ASCENDING), ("createdAt", DESCENDING)],
                name="category_created_at_desc",
            ),
        ]
    )
