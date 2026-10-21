from collections.abc import Mapping

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0002_feeds_category_and_url,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)

pytestmark = pytest.mark.integration


async def feeds_by_id(db: MongoDatabase) -> Mapping[str, Mapping[str, object]]:
    return {str(doc["_id"]): doc async for doc in db["feeds"].find()}


async def test_gives_feeds_stored_before_categories_the_other_category_and_no_url(
    db: MongoDatabase,
) -> None:
    await db["feeds"].insert_one({"_id": "old", "title": "An old feed", "source": "EL_MUNDO"})

    await m0002_feeds_category_and_url.up(db)

    assert (await feeds_by_id(db))["old"] == {
        "_id": "old",
        "title": "An old feed",
        "source": "EL_MUNDO",
        "category": "OTHER",
        "url": None,
    }


async def test_keeps_the_category_and_url_a_feed_already_has(db: MongoDatabase) -> None:
    await db["feeds"].insert_many(
        [
            {"_id": "categorized", "category": "SPORTS", "url": "https://www.elmundo.es/1.html"},
            {"_id": "cms", "category": "HEALTH", "url": None},
        ]
    )

    await m0002_feeds_category_and_url.up(db)

    feeds = await feeds_by_id(db)
    assert (feeds["categorized"]["category"], feeds["categorized"]["url"]) == (
        "SPORTS",
        "https://www.elmundo.es/1.html",
    )
    assert (feeds["cms"]["category"], feeds["cms"]["url"]) == ("HEALTH", None)


async def test_running_it_again_changes_nothing(db: MongoDatabase) -> None:
    await db["feeds"].insert_many([{"_id": "old"}, {"_id": "sports", "category": "SPORTS"}])
    await m0002_feeds_category_and_url.up(db)
    first_run = (await feeds_by_id(db), await db["feeds"].index_information())

    await m0002_feeds_category_and_url.up(db)

    assert (await feeds_by_id(db), await db["feeds"].index_information()) == first_run


async def test_creates_the_category_index_newest_first_not_unique(db: MongoDatabase) -> None:
    await m0002_feeds_category_and_url.up(db)

    index = (await db["feeds"].index_information())["category_created_at_desc"]
    assert index["key"] == [("category", 1), ("createdAt", -1)]
    assert not index.get("unique")
