---
name: ai-project-mongo-migrations
description: Add or change a MongoDB migration (indexes, data reshapes) so it is applied at startup, in order, once per database.
disable-model-invocation: false
user-invocable: false
---

# MongoDB migrations

Use automatically when a change needs MongoDB indexes, collections, or a reshape of stored data.
The rules come from `specs/improvements/I07-mongo-migrations.md`.

Migrations live in
`src/daily_trends_py/contexts/cms/shared/infrastructure/persistence/mongo/migrations/`:

- `versions/`: one module per migration, plus the ordered `MIGRATIONS` list in `__init__.py`.
- `runner.py`: `run_migrations`, which the container's Mongo client provider
  (`apps/cms_backend/providers/infrastructure.py`) calls after the ping. The lifespan builds the
  client at startup (`STARTUP_DEPENDENCIES`), so migrations run before the app takes traffic, in
  every environment.

## Add a migration

1. Create `versions/m<NNNN>_<slug>.py`. Use the next number, zero-padded to four digits. The module
   name is the migration id.

   ```python
   from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
       MongoDatabase,
   )


   async def up(db: MongoDatabase) -> None:
       await db["feeds"].create_indexes([...])
   ```

2. Append it to `MIGRATIONS` in `versions/__init__.py`:
   `Migration.from_module(m0002_<slug>)`. List order is run order. Pyright rejects a module whose
   `up` has the wrong signature.
3. Write an integration test (`pytest.mark.integration`) that runs `up` on its own database, checks
   the result, and then runs `up` a second time. The second run must succeed and leave the same
   result.

## Rules

- **Idempotent.** Running `up` again on a database where it ran, fully or partly, gives the same
  result and does not fail. A failed run is retried from the start on the next startup, and no
  transactions are used, because the development and CI server is standalone. Prefer operations
  that are idempotent by nature: `create_indexes` with explicit names, `update_many` with a filter
  that excludes documents already reshaped, and `$set` instead of `$inc`.
- **No `down`.** To undo a change, add a new migration.
- **Never edit, rename, or reorder an applied migration.** Its id is what the `migrations`
  collection records. To fix one, add a new migration.
- **Keep migrations fast and self-contained.** They block startup. Do not import application
  services or domain objects: a migration runs against the data as it is now, and later code
  changes must not change what an old migration does.
- **Never drop data automatically.** If existing data conflicts with a migration, the migration
  fails and startup exits with code 1.

## Operations

- The `migrations` collection holds one document per started migration:
  `{_id, status: "running" | "applied", started_at, applied_at}`.
- A migration that fails deletes its claim. The next startup runs it again.
- A process killed while a migration runs leaves the claim `running`. The next startup waits 60
  seconds and then fails with a message that names the migration. If no process is running it,
  delete that document from the `migrations` collection and restart.
- An applied id that is no longer in `MIGRATIONS` only logs a warning.
