from pymongo import ASCENDING, DESCENDING, IndexModel

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)


async def up(db: MongoDatabase) -> None:
    await db["feeds"].create_indexes(
        [
            # /feed/list: newest first.
            IndexModel([("createdAt", DESCENDING)], name="created_at_desc"),
            # /feed/home: the newest feeds of each source.
            IndexModel(
                [("source", ASCENDING), ("createdAt", DESCENDING)], name="source_created_at_desc"
            ),
            # Scraping: is this headline already stored this business day?
            IndexModel(
                [("source", ASCENDING), ("title", ASCENDING), ("createdAt", ASCENDING)],
                name="source_title_created_at",
            ),
        ]
    )
