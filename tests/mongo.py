import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from pymongo.errors import PyMongoError

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    create_mongo_client,
)


def _with_short_server_selection(url: str) -> str:
    # The driver waits 30 seconds by default, once per test, when Mongo is down.
    parts = urlsplit(url)
    options = dict(parse_qsl(parts.query)) | {"serverSelectionTimeoutMS": "2000"}
    return urlunsplit(parts._replace(query=urlencode(options)))


TEST_MONGO_URL = _with_short_server_selection(
    os.environ.get("MONGO_URL", "mongodb://localhost:27017/daily-trends-test")
)


def fresh_database_name(prefix: str) -> str:
    # MongoDB limits database names to 63 characters.
    return f"{prefix}-{uuid4().hex}"


def mongo_url_for(database: str) -> str:
    """The test server URL, pointing at another database."""
    return urlunsplit(urlsplit(TEST_MONGO_URL)._replace(path=f"/{database}"))


def redacted_mongo_url(url: str) -> str:
    """Only the scheme, hosts, ports and database: no credentials or options."""
    parts = urlsplit(url)
    hosts = parts.netloc.rpartition("@")[2]
    return urlunsplit((parts.scheme, hosts, parts.path, "", ""))


async def mongo_unreachable_message(url: str) -> str | None:
    try:
        client = await create_mongo_client(url)
    except PyMongoError:
        return (
            f"MongoDB is not reachable at {redacted_mongo_url(url)}; "
            "start it with: docker compose up -d --wait mongo"
        )
    await client.close()
    return None
