# I07 · Mongo migrations

**Status:** draft · **Fidelity:** new capability; no HTTP behavior changes. Depends on S01 and I04.
Resolves improvement #25 from `README.md`.

## Goal
Changes to the MongoDB schema (indexes today, data reshapes later) are written once as versioned
code and applied automatically, in order, exactly once per database, before the app takes traffic.
No external migration library is used: the Python options are unmaintained, synchronous, or too
young to depend on, and the runner needed here is small.

## Changes

### Migrations
- A migration is a Python module in
  `contexts/cms/shared/infrastructure/persistence/mongo/migrations/versions/`, named
  `m<NNNN>_<slug>.py` (`m0001_feeds_indexes.py`). Its id is the module name.
- It defines one function: `async def up(db: AsyncDatabase[MongoDocument]) -> None`.
- There is no `down`. A change is undone with a new migration.
- **Every migration is idempotent**: running it on a database where it already ran, fully or
  partly, leaves the same result and does not fail. A failed run is retried from the start on the
  next startup (see below), so this rule is what makes a retry safe.
- The ordered list of migrations is explicit, in `versions/__init__.py`. There is no file system
  discovery: pyright checks every entry, and the order is the order of the list.
- I07 ships the list empty. The first real migration, `m0001_feeds_indexes`, belongs to I08; here it
  is only an example name.
- An id never changes and an applied migration is never edited; a fix is a new migration.

### Tracking
- The `migrations` collection records one document per migration that has started:
  `{_id: <id>, status: "running" | "applied", started_at: <date>, applied_at: <date> | null}`.
- `_id` is unique, so only one process can claim a migration.

### Runner
- `runner.py` applies the pending migrations of the list, in order:
  1. Skip a migration whose document says `applied`.
  2. Claim it by inserting `{_id, status: "running", started_at: now}`.
  3. Run `up`. On success, set `status: "applied"` and `applied_at: now`.
  4. On failure, delete the claim (so the next startup retries it), log the error with the
     migration id, and stop: later migrations do not run, and the error propagates.
- **Another process holds the claim** (the insert hits the unique `_id`): wait until that
  migration is `applied`, checking every 0.5 seconds, for at most 60 seconds. If it becomes
  `applied`, continue with the next one. If the claim disappears (the other process failed), try to
  claim it again. If the wait times out, fail with
  `Migration <{id}> is still running in another process, or a crashed run left it claimed. Delete its document from the "migrations" collection if no process is running it.`
- An applied migration that is not in the list (a migration removed from the code) is logged as a
  warning and otherwise ignored.
- Each applied migration is logged at `INFO` with its id and duration.
- Mongo transactions are not used: the development and CI MongoDB is a standalone server, which
  does not support them. Idempotency covers partial runs instead.

### Startup
- The lifespan runs the runner after the Mongo ping and before the app takes traffic (S01, I04),
  in every environment, including the test database.
- A migration failure, or a claim wait that times out, is a startup failure: logged, exit code 1.
- With no pending migrations, startup costs one read of the `migrations` collection.

### Documentation
- A supporting agent skill, `ai-project-mongo-migrations` (in `.agents/skills/`, mirrored in
  `.claude/skills/`), explains how to add a migration: create the module, append it to the list,
  keep it idempotent, never edit an applied one, test it by running it twice, and clear a stale
  claim. The agent loads it only when it adds or changes a migration.
- `AGENTS.md` only references the skill in one line, so the instructions are not loaded in every
  session.

## Unchanged
- Every HTTP route and response.
- Configuration (I04): the runner uses the database of `MONGO_URL`.
- How the app connects to Mongo and closes the connection.

## Out of scope
- `down` migrations and rollback.
- A command-line tool to apply or inspect migrations.
- Checksums that detect an edited applied migration.

## Edge cases
- Empty database → every migration runs in order, and the `migrations` collection is created.
- All migrations applied → nothing runs, no writes.
- Two instances start at the same time → each migration runs once; the second instance waits and
  then starts normally.
- A migration raises → its claim is deleted, startup fails with exit code 1, the next startup runs
  it again.
- The process is killed while a migration runs → its claim stays `running`; the next startup waits
  60 seconds and then fails with the message above.
- A migration id in the database but not in the code → warning, startup continues.

## Acceptance criteria
- Runner integration tests against real Mongo, with test-only migrations:
  - applies pending migrations in list order and records them as `applied`;
  - skips applied migrations without running them again;
  - two runners in parallel on the same database run each migration once;
  - a failing migration leaves no claim, stops the later ones and raises;
  - a claim held by another process that becomes `applied` lets the runner continue;
  - a stale `running` claim fails after the wait, with the message above (the wait is
    configurable so the test runs fast).
- Startup test: a failing migration makes the app exit with code 1.
- The `ai-project-mongo-migrations` skill documents how to add a migration, and `AGENTS.md`
  references it in one line.
- `README.md` links I07 for #25.
