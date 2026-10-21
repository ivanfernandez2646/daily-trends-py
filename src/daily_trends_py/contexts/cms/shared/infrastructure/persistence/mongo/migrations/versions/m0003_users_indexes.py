from pymongo import ASCENDING, IndexModel

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)


async def up(db: MongoDatabase) -> None:
    await db["users"].create_indexes(
        [
            # Login looks users up by email, and the index is what keeps emails unique.
            IndexModel([("email", ASCENDING)], name="email_unique", unique=True),
        ]
    )
