from pymongo import TEXT, IndexModel

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)


async def up(db: MongoDatabase) -> None:
    await db["feeds"].create_indexes(
        [
            # /feed/list?q=: Spanish words, ignoring case and accents and matching their stems.
            IndexModel(
                [("title", TEXT), ("description", TEXT)],
                name="title_description_text",
                default_language="spanish",
            ),
        ]
    )
