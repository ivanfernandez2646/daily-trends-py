---
name: 'i07-mongo-migrations'
description: 'Versioned MongoDB migrations listed in code and applied at startup, in order, once per database, with a claim per migration so concurrent instances never run one twice'
spec: 'specs/improvements/I07-mongo-migrations.md'
branch: 'feat/i07-mongo-migrations'
created_at: '2026-10-12T10:00:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-12T13:00:00Z'
implemented_at: '2026-10-12T13:00:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I07 · Mongo migrations

## Goal

Resolve improvement #25. Schema changes are versioned migration modules listed in code. A small
runner applies the pending ones at startup, after the Mongo ping and before the app takes traffic.
Each migration is applied in list order and exactly once per database. A `migrations` collection
tracks them, and its unique `_id` acts as a claim, so concurrent instances never run the same
migration twice. A failure, or a claim wait that times out, stops startup with exit code 1. The
repository stays green after each phase.

## Context

- Branch `feat/i07-mongo-migrations` is cut from `main` (I01–I05 implemented, I06–I08 specs
  committed). It lives in the worktree `.claude/worktrees/i07-mongo-migrations` because I06 is
  developed in parallel in its own worktree. Both touch `apps/cms_backend/main.py`; I07 only adds
  the runner call to the lifespan and the `migrations` parameter, so a merge should be small.
- **I07 ships an empty migration list.** I08 owns the first real migration, `m0001_feeds_indexes`
  (I08 "MongoDB indexes"). In I07, `m0001_feeds_indexes` is only an example name. The runner is
  tested with test-only migrations.
- `contexts/cms/shared/infrastructure/persistence/mongo/mongo_client_factory.py` defines
  `MongoDocument = dict[str, object]`, `MongoClient`, `MongoCollection` and
  `create_mongo_client(url)`. That function builds
  `AsyncMongoClient(url, tz_aware=True, tzinfo=UTC)`, pings, and closes the client if the ping
  fails. No code imports `AsyncDatabase` yet. Repositories use `client.get_default_database()`, so
  the database name comes from `MONGO_URL`.
- `apps/cms_backend/main.py`:
  - `create_app(settings, http_transport=None)` wires everything in `lifespan`, which starts with
    `create_mongo_client(settings.mongo_url)`.
  - A lifespan error is logged by uvicorn, which exits with `STARTUP_FAILURE` (3); `main()` maps
    that to exit code 1. A migration failure therefore needs no new exit handling.
- Logging uses `logging.getLogger(__name__)`: short sentences, with the exception passed as
  `exc_info`.
- Tests:
  - `tests/mongo.py` has `TEST_MONGO_URL`, and every test shares the `daily-trends-test` database.
  - `tests/contexts/cms/conftest.py` provides a `mongo_client` fixture.
  - `tests/apps/cms_backend/test_main.py` runs `main()` in a subprocess (`run_main`, `cwd=tmp_path`)
    and asserts exit code 1.
  - Integration tests are marked `integration`.
- `specs/improvements/README.md` already links I07 for #25, so that acceptance criterion is met.
- Agent skills live in `.agents/skills/`; `.claude/skills` is a symlink to it.
- **Agreed change to the spec:** "AGENTS.md explains how to add a migration" becomes a supporting
  skill, `ai-project-mongo-migrations`, which the agent loads only when it adds a migration.
  `AGENTS.md` gets a one-line pointer to it, so the instructions are not loaded in every session.
  The I07 spec was updated to match while planning (uncommitted on the branch).

## Phase 1: Migration runner

The migration types, the empty migration list and the runner, covered by integration tests against
real Mongo. Nothing calls the runner yet.

### Public contracts

All paths are under `src/daily_trends_py/contexts/cms/shared/infrastructure/persistence/mongo/`.

- `mongo_client_factory.py`: `type MongoDatabase = AsyncDatabase[MongoDocument]`.
- `migrations/migration.py`:
  - `class MigrationModule(Protocol)`, the shape of a migration module, which pyright checks:
    - `__name__: str`
    - `async def up(self, db: MongoDatabase) -> None`
  - `@dataclass(frozen=True) class Migration`:
    - fields `id: str` and `up: Callable[[MongoDatabase], Awaitable[None]]`;
    - `@classmethod from_module(cls, module: MigrationModule) -> Migration`, whose `id` is the last
      segment of the module name (`...versions.m0001_feeds_indexes` → `m0001_feeds_indexes`).
- `migrations/versions/__init__.py`: `MIGRATIONS: Sequence[Migration] = []`. Order is list order.
  I08 appends `Migration.from_module(m0001_feeds_indexes)`.
- `migrations/runner.py`:
  - `class MigrationClaimTimeoutError(Exception)`. Its message is the spec's exact text:
    `Migration <{id}> is still running in another process, or a crashed run left it claimed. Delete its document from the "migrations" collection if no process is running it.`
  - `async def run_migrations(db: MongoDatabase, migrations: Sequence[Migration], *, claim_wait: timedelta = timedelta(seconds=60), poll_interval: timedelta = timedelta(milliseconds=500)) -> None`
- Behavior of `run_migrations`:
  - It reads the `migrations` collection once. Every applied id that is not in `migrations` logs
    a `WARNING`.
  - For each migration in list order:
    - Skip it if its document is `applied`.
    - Otherwise claim it: insert `{_id, status: "running", started_at: now, applied_at: None}`,
      run `up`, then set `status: "applied"` and `applied_at: now`.
    - Log `INFO` with the id and the duration.
  - **The claim insert hits a duplicate key:** poll the document every `poll_interval`.
    - `applied` → continue with the next migration.
    - Document gone → try to claim it again.
    - Still `running` after `claim_wait` → raise `MigrationClaimTimeoutError`.
  - **`up` raises:** `delete_one({_id, status: "running"})`, log `ERROR` with the id and the
    exception, and re-raise the original error. Later migrations do not run.
  - `now` is `datetime.now(UTC)`. This is a storage detail in infrastructure, so it does not use the
    `Clock` port.
  - With nothing pending, the only database access is the initial read.

### Tests first

- [x] `tests/contexts/cms/shared/infrastructure/persistence/mongo/migrations/test_runner.py`
      (`integration`):
  - Each test uses its own database, `daily-trends-test-mig-<uuid hex>`, on the `TEST_MONGO_URL`
    server (MongoDB limits database names to 63 characters). The database is dropped afterwards, so the shared test database never gets a
    `migrations` collection from these tests.
  - Test migrations are `Migration("m_test_<n>", up=...)`. They record their calls in a list or
    write a marker document.
  - Cases:
    - on an empty database, applies the migrations in list order and records each as `applied`
      with aware `started_at` and `applied_at`;
    - a second run skips the applied migrations without calling `up`, and writes nothing;
    - two `run_migrations` started together with `asyncio.gather` on the same database, with a
      slow first migration, call each `up` exactly once and both return;
    - a failing migration raises its error, leaves no document for its id, does not run the next
      one, and logs `ERROR` naming the id;
    - a later run applies it once it no longer fails;
    - a pre-inserted `running` claim that another task marks `applied` after a short delay lets the
      runner continue without calling that `up`;
    - a pre-inserted `running` claim that is deleted after a short delay is claimed and run by the
      runner;
    - a stale `running` claim with `claim_wait=0.2s` and `poll_interval=0.05s` raises
      `MigrationClaimTimeoutError` with the exact message;
    - an applied id that is not in the list logs a `WARNING` naming it, and the run continues;
    - each applied migration logs `INFO` with its id.
- [x] `test_migration.py` (unit): `Migration.from_module` on a test module under
      `tests/.../migrations/fixtures/` takes the id from the module name and uses its `up`.

### Implementation

- [x] Add `MongoDatabase` to `mongo_client_factory.py`.
- [x] Add `migrations/migration.py`, `migrations/versions/__init__.py` (empty `MIGRATIONS`) and
      `migrations/runner.py`.
- [x] Confirm that pyright accepts a module as a `MigrationModule` (a test fixture module passed to
      `from_module`) and rejects one with the wrong `up` signature. Verified with a throwaway
      module whose `up(db: int)` pyright rejects.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggested commits:
  - `feat(i07): add a versioned mongo migration runner`
  - `feat(i07): claim mongo migrations so concurrent instances run each once`
  - `test(i07): cover the mongo migration runner against a real database`

## Phase 2: Migrations at startup and documentation

The lifespan applies the migrations after the Mongo ping. A failure stops startup with exit code 1.
A skill explains how to add a migration, and `AGENTS.md` points to it.

### Public contracts

- `create_app(settings: Settings, http_transport: httpx.AsyncBaseTransport | None = None, migrations: Sequence[Migration] = MIGRATIONS) -> FastAPI`.
  Right after `create_mongo_client`, the lifespan awaits
  `run_migrations(mongo_client.get_default_database(), migrations)`. If that raises, the lifespan
  closes the Mongo client and re-raises.
- `main(migrations: Sequence[Migration] = MIGRATIONS) -> None` passes them to `create_app`. The
  parameter lets the startup test inject a failing migration without patching imports.
  `[project.scripts]` keeps calling `main()`.
- New skill `ai-project-mongo-migrations` (`user-invocable: false`, selected by the agent when it
  adds or changes a MongoDB migration), in `.agents/skills/` (`.claude/skills` links to it). It
  covers:
  - creating `versions/m<NNNN>_<slug>.py` with `async def up(db: MongoDatabase) -> None`;
  - appending `Migration.from_module(...)` to `MIGRATIONS`;
  - keeping the migration idempotent, with the reason (a failed run is retried from the start);
  - no `down`, never editing or renaming an applied migration, and fixing one with a new
    migration;
  - no transactions;
  - how to test the migration, including running it twice;
  - how to clear a stale claim.
- `AGENTS.md`: one line under "Architecture" or "Quality rules" saying that MongoDB schema changes
  are migrations and that the `ai-project-mongo-migrations` skill explains how to add one.

### Tests first

- [x] `tests/apps/cms_backend/test_main.py` (`integration`):
  - `run_main` runs `main(migrations=[failing])` against a fresh database
    (`MONGO_URL=<server>/daily-trends-test-startup-<uuid hex>`) and exits with code 1. stderr has
    the runner's `Migration m_test_fails failed` log line. The database is dropped afterwards.
  - The failing migration is defined inline in the subprocess script; the subprocess runs outside
    the repository, where the `tests` package is not importable. Asserting only the id gave a
    false positive before the change: the traceback of the old `main()` quoted the script line.
- [x] `tests/apps/cms_backend/test_app.py` (`integration`): starting the app with a recording
      migration on a fresh database applies it before the first request is served, and records it
      in `migrations`. `tests/mongo.py` gains `fresh_database_name` and `mongo_url_for`.
- [x] The existing app tests keep passing with `MIGRATIONS` empty on the shared test database,
      which gets no `migrations` collection (the empty run only reads).

### Implementation

- [x] Add the `migrations` parameter to `create_app` and `main`, and call `run_migrations` in the
      lifespan after the ping, closing the client on failure.
- [x] Add the `ai-project-mongo-migrations` skill in `.agents/skills/` (one copy, through the
      symlink), and the pointer in `AGENTS.md` after the composition root paragraph.
- [x] Update `specs/improvements/I07-mongo-migrations.md` (done while planning):
  - "Documentation" and the acceptance criterion now say that the skill documents migrations and
    `AGENTS.md` references it;
  - note that I07 ships an empty list and that `m0001_feeds_indexes` belongs to I08.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggested commits:
  - `feat(i07): apply mongo migrations at startup`
  - `docs(i07): add a skill explaining how to add a mongo migration`
  - `test(i07): fail startup with exit code 1 when a migration fails`

## Next step

Every phase is implemented. After review, commit Phase 2, then merge `feat/i07-mongo-migrations`.
I08 adds `m0001_feeds_indexes` as the first migration.
