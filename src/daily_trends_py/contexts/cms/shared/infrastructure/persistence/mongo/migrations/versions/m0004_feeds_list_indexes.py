from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import OperationFailure

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)

_INDEX_NOT_FOUND = 27

# The list indexes of m0001 and m0002, which end in the creation date alone.
_REPLACED = ("created_at_desc", "category_created_at_desc", "source_created_at_desc")


async def up(db: MongoDatabase) -> None:
    feeds = db["feeds"]
    # Created before the old ones are dropped, so the list always has an index to read.
    await feeds.create_indexes(
        [
            # /feed/list: newest first, the id ordering feeds of the same scraping run.
            IndexModel([("createdAt", DESCENDING), ("_id", DESCENDING)], name="created_at_id_desc"),
            # /feed/list?category=.
            IndexModel(
                [("category", ASCENDING), ("createdAt", DESCENDING), ("_id", DESCENDING)],
                name="category_created_at_id_desc",
            ),
            # /feed/list?source= and /feed/home.
            IndexModel(
                [("source", ASCENDING), ("createdAt", DESCENDING), ("_id", DESCENDING)],
                name="source_created_at_id_desc",
            ),
        ]
    )
    for name in _REPLACED:
        try:
            await feeds.drop_index(name)
        except OperationFailure as error:
            if error.code != _INDEX_NOT_FOUND:
                raise
