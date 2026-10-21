import pytest
from pymongo.errors import DuplicateKeyError

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0003_users_indexes,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)

pytestmark = pytest.mark.integration


async def test_creates_a_unique_index_on_the_user_email(db: MongoDatabase) -> None:
    await m0003_users_indexes.up(db)

    index = (await db["users"].index_information())["email_unique"]
    assert index["key"] == [("email", 1)]
    assert index["unique"] is True


async def test_the_index_rejects_a_second_user_with_the_same_email(db: MongoDatabase) -> None:
    await m0003_users_indexes.up(db)
    await db["users"].insert_one({"_id": "first", "email": "admin@example.com"})

    with pytest.raises(DuplicateKeyError):
        await db["users"].insert_one({"_id": "second", "email": "admin@example.com"})


async def test_running_it_again_changes_nothing(db: MongoDatabase) -> None:
    await m0003_users_indexes.up(db)
    first_run = await db["users"].index_information()

    await m0003_users_indexes.up(db)

    assert await db["users"].index_information() == first_run
