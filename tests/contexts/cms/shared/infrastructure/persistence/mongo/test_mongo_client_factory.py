import pytest
from pymongo.errors import ServerSelectionTimeoutError

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    create_mongo_client,
)


@pytest.mark.integration
async def test_returns_a_connected_client(mongo_client: MongoClient) -> None:
    result = await mongo_client.admin.command("ping")

    assert result["ok"] == 1


async def test_fails_when_mongo_is_unreachable() -> None:
    with pytest.raises(ServerSelectionTimeoutError):
        await create_mongo_client("mongodb://localhost:1/daily-trends?serverSelectionTimeoutMS=100")
