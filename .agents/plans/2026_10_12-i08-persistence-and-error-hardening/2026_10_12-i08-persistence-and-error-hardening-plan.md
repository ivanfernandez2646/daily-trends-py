---
name: 'i08-persistence-and-error-hardening'
description: 'Atomic create and update, generic 500 bodies, indexes on feeds as the first migration, and a test session that fails fast without MongoDB'
spec: 'specs/improvements/I08-persistence-and-error-hardening.md'
branch: 'fix/i08-persistence-and-error-hardening'
created_at: '2026-10-12T15:00:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-20T09:17:12Z'
implemented_at: '2026-10-20T09:17:12Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I08 · Persistence and error hardening

## Goal

Resolve improvements #21–#24. Concurrent writes cannot overwrite or resurrect a feed, because the
database decides conflicts through `create` (insert) and `update` (no upsert). Every 500 answers
`{"error": "Internal server error"}` and logs the original error with its method and path.
`m0001_feeds_indexes` creates the three indexes the API uses every day. Without MongoDB, a test
session fails after one 2-second check instead of hanging. The repository stays green after each
phase.

## Context

- `main` already has I06 (`80507dd`) and I07 (`0fb4b3c`).
- **Port.** `FeedRepository` (`contexts/cms/feeds/domain/feed_repository.py`) has `save`, `find`,
  `delete`, `search` and `exists_headline`.
- **Shared base.** `MongoRepository._persist`
  (`contexts/cms/shared/infrastructure/persistence/mongo/mongo_repository.py:15-18`) runs
  `update_one({"_id": id}, {"$set": ...}, upsert=True)`. Its own tests
  (`tests/contexts/cms/shared/infrastructure/persistence/mongo/test_mongo_repository.py`) use a
  `ThingMongoRepository.save`.
- **Callers of `save`:**
  - `FeedCreator` at line 39, which runs `find` and raises `FeedAlreadyExists` first (L33-34).
  - `FeedUpdater` at line 32, which runs `find_feed` first.
  - `FeedScraper` at line 42.
  - Acceptance seeding: `tests/apps/cms_backend/conftest.py:107`, `test_list_feeds.py:30`,
    `test_home_feeds.py:47,60`, `test_scrap_feeds.py:79` and `test_feed_json.py:46`.
  - Mongo repository tests.
- **Fakes.**
  - `InMemoryFeedRepository` (`tests/contexts/cms/feeds/fakes/`) upserts in `save` and records
    `saved`.
  - `FailingFeedRepository` overrides `save`. It is used in the scraper, home refresher and home
    searcher tests.
- **500.** Only `UnhandledErrorMiddleware` (`apps/cms_backend/errors.py:47-77`) produces it. It logs
  `"Unhandled error"` with `exc_info` (no method or path) and answers `str(error)`.
  - `tests/apps/cms_backend/test_errors.py:74` and `test_app.py:21` assert on that body and log.
  - `test_invalid_stored_feed.py` asserts the `Stored feed <id> is invalid: ...` body for six
    routes, including `PUT`.
- **Migrations.** `versions/__init__.py` has `MIGRATIONS = []`. The
  `ai-project-mongo-migrations` skill describes how to add one. The `db` fixture in
  `tests/.../mongo/migrations/conftest.py` gives each test its own database.
- **Test Mongo access.**
  - `tests/mongo.py` reads `TEST_MONGO_URL` from `MONGO_URL` and sets no
    `serverSelectionTimeoutMS`, so the driver waits 30 seconds.
  - There is no root `tests/conftest.py`.
  - Integration tests are marked `integration`, by module or one by one. Tests that only build a
    container (`test_openapi.py`, `test_errors.py`, `http/test_json_body_route.py`) never connect.
- **Scope.** The I07 spec still says `draft`. Changing spec statuses is out of scope.

### Agreed decisions

- Granularity: intermediate, 4 phases, one per README item. The spec notes go in the last phase.
- The shared base returns `bool`. `MongoFeedRepository` maps `False` to the domain error, so the
  base knows nothing about feeds. The base translates only a `DuplicateKeyError` on `_id`; any
  other duplicate key is raised again.
- The fake records `created` and `updated` instead of `saved`, so tests can tell the two writes
  apart.
- The short test timeout is a URL option (`serverSelectionTimeoutMS=2000`) added to
  `TEST_MONGO_URL`. Production code and settings do not change.
- The session check lives in a new root `tests/conftest.py`. It runs once after collection, and
  only when a selected test is marked `integration`. When Mongo does not answer it calls
  `pytest.exit(message, returncode=1)`. Its logic is a plain function in `tests/mongo.py`, so it
  can be unit-tested with an unreachable URL.
- The concurrent `PUT` acceptance test sends both requests from two threads through the shared
  `TestClient`. They run concurrently on the app's event loop.

## Phase 1: Atomic create and update (#21)

The port replaces `save` with `create` and `update`, and the database decides conflicts.
`FeedCreator` no longer reads before it writes. A `PATCH` that races a `DELETE` answers 404. A
`PUT` on an id whose stored document is invalid answers 409.

### Public contracts

- `FeedRepository`:
  - `async def create(self, feed: Feed) -> None`. Raises `FeedAlreadyExists(feed.id)` and changes
    nothing.
  - `async def update(self, feed: Feed) -> None`. Raises `FeedNotFound(feed.id)` and inserts
    nothing.
  - `save` is removed.
- `MongoRepository` (shared base):
  - `async def _insert(self, id: str, primitives: Mapping[str, object]) -> bool`. Uses
    `insert_one` and returns `False` on a duplicate `_id`.
  - `async def _update(self, id: str, primitives: Mapping[str, object]) -> bool`. Uses
    `update_one` with `$set` and no upsert, and returns `matched_count == 1`.
  - `_persist` is removed.
- `MongoFeedRepository.create` and `MongoFeedRepository.update` raise the domain errors.
- Use cases:
  - `FeedCreator.execute` validates, then calls `create`, with no `find`.
  - `FeedUpdater.execute` calls `find_feed`, then `update`.
  - `FeedScraper` calls `create`, and a `FeedAlreadyExists` there propagates.
- `InMemoryFeedRepository`:
  - `create` and `update` follow the port rules.
  - `created: list[Feed]` and `updated: list[Feed]` replace `saved`.
- `FailingFeedRepository(*, creates_before_failing: int, error: Exception, feeds=None)` fails on
  `create`.
- HTTP: `PUT /feed/{id}` on an id with an invalid stored document answers 409. It used to answer
  500.

### Tests first

- [x] Fake: `create` on an existing id raises `FeedAlreadyExists` and keeps the stored feed.
- [x] Fake: `update` on a missing id raises `FeedNotFound` and stores nothing.
- [x] `FeedCreator`: raises `FeedAlreadyExists` coming from `create`, does not call `find` (empty
  `searched_ids`) and publishes nothing.
- [x] `FeedCreator`: still raises the first invalid argument before it writes.
- [x] `FeedUpdater`: raises `FeedNotFound` coming from `update` when the feed disappears between
  `find` and the write. Use a fake that deletes the feed before `update`, or one that holds a feed
  `find` returns but `update` does not.
- [x] `FeedUpdater`: a `PATCH` with no changes still writes nothing (`updated` stays empty).
- [x] `FeedScraper`: new feeds are stored with `create`.
- [x] `FeedScraper`: a `FeedAlreadyExists` from `create` propagates and keeps the feeds already
  stored.
- [x] Mongo base (`test_mongo_repository.py`):
  - `_insert` stores the document under `_id`.
  - `_insert` on an existing id returns `False` and keeps the original document.
  - `_update` sets the sent fields and keeps the others.
  - `_update` on a missing id returns `False` and inserts nothing.
- [x] `MongoFeedRepository`:
  - `create` on an existing id raises `FeedAlreadyExists` and keeps the original document.
  - `update` on a missing id raises `FeedNotFound` and inserts nothing.
  - `update` replaces the stored feed's fields.
- [x] Acceptance: two concurrent `PUT /feed/{id}` with the same id and different bodies give
  exactly one 201 and one 409. `GET /feed/{id}` returns the body from the 201.
- [x] Acceptance: `PUT` on an id with an invalid stored document answers 409 with the
  `FeedAlreadyExists` message. Move this case out of the parametrized 500 test.

### Implementation

- [x] Replace `_persist` with `_insert` and `_update` in `MongoRepository`, and update
  `ThingMongoRepository` and its tests.
- [x] Replace `save` with `create` and `update` in the port, `MongoFeedRepository`, the
  in-memory fake and the failing fake.
- [x] Update `FeedCreator` (drop the `find`), `FeedUpdater` and `FeedScraper`.
- [x] Update the use-case tests that assert `saved` to assert `created` or `updated`.
- [x] Switch acceptance seeding and the Mongo repository tests from `save` to `create`.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Generic 500 responses (#22)

A 500 never shows internal details. The client always gets the same body, and the log keeps the
original error, its traceback, the method and the path.

### Public contracts

- Every 500 answers `{"error": "Internal server error"}`. This includes `InvalidStoredFeed`.
- `UnhandledErrorMiddleware` logs
  `logger.error("Unhandled error on %s %s", method, path, exc_info=error)`.
- 4xx bodies are unchanged.
- OpenAPI: if the description in `main.py` or `_ERROR_DESCRIPTIONS` states that the 500 body
  carries the error message, it now states the fixed message.

### Tests first

- [x] `test_errors.py`: an error of no kind answers 500 with `{"error": "Internal server error"}`.
  The captured log has the original message, the traceback, the method and the path.
- [x] `test_app.py`: the 500 is still JSON with CORS headers and is logged once, now with the
  generic body.
- [x] `test_invalid_stored_feed.py`: `GET`, `PATCH` and `DELETE /feed/{id}`, `GET /feed/list` and
  `GET /feed/home` answer `{"error": "Internal server error"}`. The captured log contains
  `Stored feed <id> is invalid: ...`, the method and the path.
- [x] Existing 400, 404 and 409 tests keep passing unchanged.

### Implementation

- [x] Answer `error_response(500, "Internal server error")` in the middleware and log the method
  and path from `scope`.
- [x] Adjust the OpenAPI or description text if it promises the error message.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 3: MongoDB indexes (#23)

The first migration creates the indexes for the listing, the front page and headline
deduplication. Following the `ai-project-mongo-migrations` skill, it is applied at startup once
per database.

### Public contracts

- `contexts/cms/shared/infrastructure/persistence/mongo/migrations/versions/m0001_feeds_indexes.py`
  provides `async def up(db: MongoDatabase) -> None`. It calls `db["feeds"].create_indexes` with
  these indexes:

  | Name | Keys |
  |---|---|
  | `created_at_desc` | `createdAt: -1` |
  | `source_created_at_desc` | `source: 1, createdAt: -1` |
  | `source_title_created_at` | `source: 1, title: 1, createdAt: 1` |

  None of them is unique. It imports nothing from the domain or application layers.
- `MIGRATIONS = [Migration.from_module(m0001_feeds_indexes)]`.

### Tests first

- [x] Integration test, on its own database from the `db` fixture: after `up`, `feeds` has exactly
  `_id_` plus the three indexes, with the names and keys above, and none of them is unique.
- [x] Integration test: running `up` a second time succeeds and leaves the same indexes.
- [x] Integration test: if an index with the same keys but another name already exists, `up`
  raises and that index is not dropped.
- [x] `MIGRATIONS` lists `m0001_feeds_indexes` first. This can be a unit test on the ids.
- [x] Startup on a database where `m0001_feeds_indexes` is already applied does not run it again.
  The runner tests already cover this; add a test only if they do not use the real list.

### Implementation

- [x] Add the module and append it to `MIGRATIONS`.
- [x] Check that the acceptance tests still pass now that startup applies the migration to
  `daily-trends-test`.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 4: Test session fails fast without MongoDB (#24) and spec notes

Tests use a 2-second server selection timeout. Reachability is checked once per session, and only
when integration tests are selected. When Mongo does not answer, the session fails at once with a
message whose URL hides credentials. The S01, I01 and README notes close the spec.

### Public contracts

- `tests/mongo.py`:
  - `TEST_MONGO_URL` carries `serverSelectionTimeoutMS=2000`. It keeps any query options that
    `MONGO_URL` already has.
  - `redacted_mongo_url(url: str) -> str` keeps only the scheme, host, port and database.
  - `async def mongo_unreachable_message(url: str) -> str | None` pings once. It returns
    `MongoDB is not reachable at <redacted url>; start it with: docker compose up -d --wait mongo`,
    or `None` when Mongo answers.
- `tests/conftest.py` (new): a `pytest_collection_modifyitems` (or `pytest_runtestloop`) hook. When
  any selected item has the `integration` marker, it runs the check once and calls
  `pytest.exit(message, returncode=1)` on failure.
- `pyproject.toml`: the marker descriptions are unchanged, and there is no `addopts` deselection,
  so `network` tests still run by default.
- Docs:
  - `S01` gets a "Superseded by I08" note on "upsert by `_id`" and "500 with `err.message`".
  - `I01` gets the same note on the 500 body for invalid stored data.
  - `specs/improvements/README.md` links I08 for #21–#24.

### Tests first

- [x] `redacted_mongo_url`:
  - `mongodb://user:secret@host:27017/db?authSource=admin&serverSelectionTimeoutMS=2000` becomes
    `mongodb://host:27017/db`.
  - A URL without credentials is kept as scheme, host, port and database.
- [x] `mongo_unreachable_message` on an unreachable URL, for example a closed local port with a
  short timeout, returns the spec message, shows no credentials, and answers within a few seconds.
- [x] `mongo_unreachable_message` on `TEST_MONGO_URL` returns `None`. This test is marked
  `integration`.
- [x] `TEST_MONGO_URL` has `serverSelectionTimeoutMS=2000` and keeps existing options.
- [x] Session behavior, through a `pytester` test or a subprocess run of `pytest` with
  `MONGO_URL` on a closed port:
  - With an integration test selected, it exits with code 1 within a few seconds and prints the
    message.
  - With `-m "not integration"`, it passes and never contacts Mongo.

### Implementation

- [x] Add the URL helpers and the check to `tests/mongo.py`, and the hook to `tests/conftest.py`.
- [x] Run `MONGO_URL=mongodb://localhost:1/daily-trends-test uv run pytest -m "not integration"`.
  Mark `integration` any test that fails because it needs Mongo.
- [x] Run `uv run pytest` with Mongo stopped and confirm it fails in seconds with the message.
- [x] Add the spec notes and the README links.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Every phase is implemented. After review, commit Phase 4, then merge
`fix/i08-persistence-and-error-hardening`.

Notes from Phase 4:
- The session check runs as the last `pytest_collection_modifyitems`, after `-m` has deselected
  items, and never under `--collect-only`.
- `-m "not integration"` with `MONGO_URL` on a closed port passed (277 tests), so no unmarked test
  needed Mongo. `uv run pytest` with the Mongo container stopped exited with code 1 in about 3
  seconds with the message.
- `specs/improvements/README.md` already linked I08 for #21–#24. The project README now documents
  `-m "not integration"` and the fast failure.
