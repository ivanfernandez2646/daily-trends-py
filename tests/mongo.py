import os
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

TEST_MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/daily-trends-test")


def fresh_database_name(prefix: str) -> str:
    # MongoDB limits database names to 63 characters.
    return f"{prefix}-{uuid4().hex}"


def mongo_url_for(database: str) -> str:
    """The test server URL, pointing at another database."""
    return urlunsplit(urlsplit(TEST_MONGO_URL)._replace(path=f"/{database}"))
