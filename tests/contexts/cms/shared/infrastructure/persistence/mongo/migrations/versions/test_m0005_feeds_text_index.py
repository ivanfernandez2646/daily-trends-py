from collections.abc import Mapping

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0005_feeds_text_index,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)

pytestmark = pytest.mark.integration


async def text_index(db: MongoDatabase) -> Mapping[str, object]:
    return (await db["feeds"].index_information())["title_description_text"]


async def test_creates_a_spanish_text_index_over_the_title_and_the_description(
    db: MongoDatabase,
) -> None:
    await m0005_feeds_text_index.up(db)

    index = await text_index(db)
    assert index["key"] == [("_fts", "text"), ("_ftsx", 1)]
    assert index["weights"] == {"title": 1, "description": 1}
    assert index["default_language"] == "spanish"


async def test_running_it_again_changes_nothing(db: MongoDatabase) -> None:
    await m0005_feeds_text_index.up(db)
    first_run = await db["feeds"].index_information()

    await m0005_feeds_text_index.up(db)

    assert await db["feeds"].index_information() == first_run
