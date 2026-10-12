import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)
from tests.contexts.cms.shared.infrastructure.persistence.mongo.migrations.fixtures import (
    m9001_create_marker,
)


def test_from_module_takes_the_id_from_the_module_name() -> None:
    migration = Migration.from_module(m9001_create_marker)

    assert migration.id == "m9001_create_marker"


@pytest.mark.integration
async def test_from_module_runs_the_module_up(db: MongoDatabase) -> None:
    migration = Migration.from_module(m9001_create_marker)

    await migration.up(db)

    assert await db["markers"].find_one({"_id": "m9001"}) == {"_id": "m9001"}
