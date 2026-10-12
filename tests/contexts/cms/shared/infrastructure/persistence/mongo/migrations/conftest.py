from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoDatabase,
)


@pytest.fixture
async def db(mongo_client: MongoClient) -> AsyncIterator[MongoDatabase]:
    # Its own database, so a "migrations" collection never reaches the shared test database.
    db = mongo_client[f"daily-trends-test-mig-{uuid4().hex}"]
    yield db
    await mongo_client.drop_database(db.name)
