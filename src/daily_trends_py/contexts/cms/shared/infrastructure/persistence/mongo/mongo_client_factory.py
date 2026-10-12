from datetime import UTC

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

type MongoDocument = dict[str, object]
type MongoClient = AsyncMongoClient[MongoDocument]
type MongoCollection = AsyncCollection[MongoDocument]
type MongoDatabase = AsyncDatabase[MongoDocument]


async def create_mongo_client(url: str) -> MongoClient:
    # Dates come back as aware UTC datetimes, as the domain requires.
    client: MongoClient = AsyncMongoClient(url, tz_aware=True, tzinfo=UTC)
    # Connecting is lazy; a ping makes an unreachable server fail before the app takes traffic.
    try:
        await client.admin.command("ping")
    except Exception:
        await client.close()
        raise
    return client
