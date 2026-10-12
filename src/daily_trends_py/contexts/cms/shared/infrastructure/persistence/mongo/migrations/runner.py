import asyncio
import logging
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from pymongo.errors import DuplicateKeyError

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoCollection,
    MongoDatabase,
)

logger = logging.getLogger(__name__)

COLLECTION = "migrations"
APPLIED = "applied"
RUNNING = "running"


class MigrationClaimTimeoutError(Exception):
    def __init__(self, id: str) -> None:
        super().__init__(
            f"Migration <{id}> is still running in another process, or a crashed run left it "
            f'claimed. Delete its document from the "{COLLECTION}" collection if no process is '
            "running it."
        )


async def run_migrations(
    db: MongoDatabase,
    migrations: Sequence[Migration],
    *,
    claim_wait: timedelta = timedelta(seconds=60),
    poll_interval: timedelta = timedelta(milliseconds=500),
) -> None:
    collection = db[COLLECTION]
    statuses = {doc["_id"]: doc["status"] async for doc in collection.find()}
    known = {migration.id for migration in migrations}
    for id, status in statuses.items():
        if status == APPLIED and id not in known:
            logger.warning("Applied migration %s is not in the code", id)

    for migration in migrations:
        if statuses.get(migration.id) != APPLIED:
            await _apply(collection, migration, claim_wait, poll_interval)


async def _apply(
    collection: MongoCollection,
    migration: Migration,
    claim_wait: timedelta,
    poll_interval: timedelta,
) -> None:
    deadline = time.monotonic() + claim_wait.total_seconds()
    while not await _claim(collection, migration.id):
        # Another process holds the claim: wait until it applies the migration or gives it up.
        while (doc := await collection.find_one({"_id": migration.id})) is not None:
            if doc["status"] == APPLIED:
                return
            if time.monotonic() >= deadline:
                raise MigrationClaimTimeoutError(migration.id)
            await asyncio.sleep(poll_interval.total_seconds())

    started = time.monotonic()
    try:
        await migration.up(collection.database)
    except Exception as error:
        # Without the claim, the next startup runs the migration again from the start.
        await collection.delete_one({"_id": migration.id, "status": RUNNING})
        logger.error("Migration %s failed", migration.id, exc_info=error)
        raise
    await collection.update_one(
        {"_id": migration.id}, {"$set": {"status": APPLIED, "applied_at": datetime.now(UTC)}}
    )
    logger.info("Applied migration %s in %.3fs", migration.id, time.monotonic() - started)


async def _claim(collection: MongoCollection, id: str) -> bool:
    try:
        await collection.insert_one(
            {"_id": id, "status": RUNNING, "started_at": datetime.now(UTC), "applied_at": None}
        )
    except DuplicateKeyError:
        return False
    return True
