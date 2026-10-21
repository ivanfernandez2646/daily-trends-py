import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.runner import (
    run_migrations,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    MIGRATIONS,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)


def test_lists_the_migrations_in_the_order_they_are_applied() -> None:
    assert [migration.id for migration in MIGRATIONS] == [
        "m0001_feeds_indexes",
        "m0002_feeds_category_and_url",
    ]


@pytest.mark.integration
async def test_a_database_with_every_migration_applied_runs_none_again(db: MongoDatabase) -> None:
    await run_migrations(db, MIGRATIONS)
    applied = [doc async for doc in db["migrations"].find()]

    await run_migrations(db, MIGRATIONS)

    assert [doc async for doc in db["migrations"].find()] == applied
    assert [doc["_id"] for doc in applied] == [migration.id for migration in MIGRATIONS]
