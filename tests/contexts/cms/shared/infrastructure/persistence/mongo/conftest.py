import os
from collections.abc import AsyncIterator

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    create_mongo_client,
)

TEST_MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/daily-trends-test")


@pytest.fixture
async def mongo_client() -> AsyncIterator[MongoClient]:
    client = await create_mongo_client(TEST_MONGO_URL)
    yield client
    await client.close()
