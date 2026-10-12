import asyncio
import logging
from datetime import UTC, datetime, timedelta

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.runner import (
    MigrationClaimTimeoutError,
    run_migrations,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)

pytestmark = pytest.mark.integration

FAST_POLL = timedelta(milliseconds=10)


class RecordingMigrations:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def migration(
        self, id: str, *, duration: float = 0, error: Exception | None = None
    ) -> Migration:
        async def up(db: MongoDatabase) -> None:
            self.calls.append(id)
            await asyncio.sleep(duration)
            if error is not None:
                raise error

        return Migration(id, up)


async def claim(db: MongoDatabase, id: str) -> None:
    await db["migrations"].insert_one(
        {"_id": id, "status": "running", "started_at": datetime.now(UTC), "applied_at": None}
    )


async def statuses(db: MongoDatabase) -> dict[object, object]:
    return {doc["_id"]: doc["status"] async for doc in db["migrations"].find()}


async def test_applies_pending_migrations_in_list_order_and_records_them(
    db: MongoDatabase,
) -> None:
    recording = RecordingMigrations()

    await run_migrations(db, [recording.migration("m_b"), recording.migration("m_a")])

    assert recording.calls == ["m_b", "m_a"]
    documents = [doc async for doc in db["migrations"].find()]
    assert {doc["_id"] for doc in documents} == {"m_a", "m_b"}
    for doc in documents:
        started_at, applied_at = doc["started_at"], doc["applied_at"]
        assert doc["status"] == "applied"
        assert isinstance(started_at, datetime) and started_at.tzinfo is not None
        assert isinstance(applied_at, datetime) and applied_at >= started_at


async def test_skips_applied_migrations_without_writing(db: MongoDatabase) -> None:
    recording = RecordingMigrations()
    migrations = [recording.migration("m_a"), recording.migration("m_b")]
    await run_migrations(db, migrations)
    applied = [doc async for doc in db["migrations"].find()]

    await run_migrations(db, migrations)

    assert recording.calls == ["m_a", "m_b"]
    assert [doc async for doc in db["migrations"].find()] == applied


async def test_parallel_runners_apply_each_migration_once(db: MongoDatabase) -> None:
    recording = RecordingMigrations()
    migrations = [recording.migration("m_a", duration=0.2), recording.migration("m_b")]

    await asyncio.gather(
        run_migrations(db, migrations, poll_interval=FAST_POLL),
        run_migrations(db, migrations, poll_interval=FAST_POLL),
    )

    assert recording.calls == ["m_a", "m_b"]
    assert await statuses(db) == {"m_a": "applied", "m_b": "applied"}


async def test_failing_migration_releases_its_claim_and_stops_the_later_ones(
    db: MongoDatabase, caplog: pytest.LogCaptureFixture
) -> None:
    recording = RecordingMigrations()
    error = RuntimeError("boom")

    with pytest.raises(RuntimeError) as raised:
        await run_migrations(
            db,
            [
                recording.migration("m_a"),
                recording.migration("m_b", error=error),
                recording.migration("m_c"),
            ],
        )

    assert raised.value is error
    assert recording.calls == ["m_a", "m_b"]
    assert await statuses(db) == {"m_a": "applied"}
    [record] = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert "m_b" in record.getMessage()
    assert record.exc_info is not None and record.exc_info[1] is error


async def test_failed_migration_runs_again_on_the_next_run(db: MongoDatabase) -> None:
    recording = RecordingMigrations()
    with pytest.raises(RuntimeError):
        await run_migrations(db, [recording.migration("m_a", error=RuntimeError("boom"))])

    await run_migrations(db, [recording.migration("m_a")])

    assert recording.calls == ["m_a", "m_a"]
    assert await statuses(db) == {"m_a": "applied"}


async def test_continues_when_a_claim_held_elsewhere_becomes_applied(db: MongoDatabase) -> None:
    recording = RecordingMigrations()
    await claim(db, "m_a")

    async def apply_elsewhere() -> None:
        await asyncio.sleep(0.1)
        await db["migrations"].update_one(
            {"_id": "m_a"}, {"$set": {"status": "applied", "applied_at": datetime.now(UTC)}}
        )

    elsewhere = asyncio.create_task(apply_elsewhere())
    await run_migrations(
        db, [recording.migration("m_a"), recording.migration("m_b")], poll_interval=FAST_POLL
    )
    await elsewhere

    assert recording.calls == ["m_b"]
    assert await statuses(db) == {"m_a": "applied", "m_b": "applied"}


async def test_claims_again_when_a_claim_held_elsewhere_disappears(db: MongoDatabase) -> None:
    recording = RecordingMigrations()
    await claim(db, "m_a")

    async def fail_elsewhere() -> None:
        await asyncio.sleep(0.1)
        await db["migrations"].delete_one({"_id": "m_a"})

    elsewhere = asyncio.create_task(fail_elsewhere())
    await run_migrations(db, [recording.migration("m_a")], poll_interval=FAST_POLL)
    await elsewhere

    assert recording.calls == ["m_a"]
    assert await statuses(db) == {"m_a": "applied"}


async def test_fails_when_a_stale_claim_outlasts_the_wait(db: MongoDatabase) -> None:
    recording = RecordingMigrations()
    await claim(db, "m_a")

    with pytest.raises(MigrationClaimTimeoutError) as raised:
        await run_migrations(
            db,
            [recording.migration("m_a"), recording.migration("m_b")],
            claim_wait=timedelta(milliseconds=200),
            poll_interval=timedelta(milliseconds=50),
        )

    assert str(raised.value) == (
        "Migration <m_a> is still running in another process, or a crashed run left it claimed. "
        'Delete its document from the "migrations" collection if no process is running it.'
    )
    assert recording.calls == []
    assert await statuses(db) == {"m_a": "running"}


async def test_warns_about_applied_migrations_missing_from_the_list(
    db: MongoDatabase, caplog: pytest.LogCaptureFixture
) -> None:
    recording = RecordingMigrations()
    await claim(db, "m_removed")
    await db["migrations"].update_one({"_id": "m_removed"}, {"$set": {"status": "applied"}})

    await run_migrations(db, [recording.migration("m_a")])

    assert recording.calls == ["m_a"]
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert ["m_removed" in record.getMessage() for record in warnings] == [True]


async def test_logs_each_applied_migration(
    db: MongoDatabase, caplog: pytest.LogCaptureFixture
) -> None:
    recording = RecordingMigrations()
    caplog.set_level(logging.INFO)

    await run_migrations(db, [recording.migration("m_a"), recording.migration("m_b")])

    infos = [record.getMessage() for record in caplog.records if record.levelno == logging.INFO]
    assert any("m_a" in message for message in infos)
    assert any("m_b" in message for message in infos)
