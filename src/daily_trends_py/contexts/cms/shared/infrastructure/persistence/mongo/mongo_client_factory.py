from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection

type MongoDocument = dict[str, object]
type MongoClient = AsyncMongoClient[MongoDocument]
type MongoCollection = AsyncCollection[MongoDocument]


async def create_mongo_client(url: str) -> MongoClient:
    client: MongoClient = AsyncMongoClient(url)
    # Connecting is lazy; a ping makes an unreachable server fail before the app takes traffic.
    try:
        await client.admin.command("ping")
    except Exception:
        await client.close()
        raise
    return client
