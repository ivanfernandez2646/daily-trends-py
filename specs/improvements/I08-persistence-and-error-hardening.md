# I08 · Persistence and error hardening

**Status:** draft · **Fidelity:** intentional break with the ported behavior. Depends on S00–S07,
I01–I05 and I07 (the indexes are its first migration). Independent of I06; if I06 is implemented
first, the 500 rule below applies to its exception handlers. Resolves improvements #21, #22, #23
and #24 from `README.md`.

## Goal
Concurrent writes cannot silently overwrite or resurrect a feed, a 500 never shows internal details
to the client, the queries the API runs every day use indexes, and a test run without MongoDB fails
in seconds instead of hanging.

## Changes

### Atomic create (#21)
Today `PUT /feed/{id}` checks `find` and then calls `save`, an upsert. Two concurrent `PUT` with
the same id both pass the check, both answer 201, and the second one overwrites the first.

- The `FeedRepository` port splits writes in two:
  - `create(feed)`: inserts a new feed. If a feed with that id already exists it raises
    `FeedAlreadyExists` and changes nothing. In Mongo: `insert_one`, translating
    `DuplicateKeyError` on `_id`.
  - `update(feed)`: replaces an existing feed. If no feed with that id exists it raises
    `FeedNotFound` and changes nothing. In Mongo: `update_one` **without** upsert, checking
    `matched_count`.
  - `save` (upsert) is removed.
- `FeedCreator` validates the input and calls `create`; it no longer calls `find` first. The
  database decides the conflict.
- `FeedUpdater` calls `update`. A `PATCH` that races a `DELETE` answers 404 instead of bringing the
  feed back.
- `FeedScraper` stores new feeds with `create`. A `FeedAlreadyExists` there is a programming error
  (ids are random UUIDs) and propagates as a 500, like any other save error (I01).
- The in-memory fake repository follows the same rules, so use-case tests cover both errors.

### Generic 500 responses (#22)
Today a 500 returns `str(error)`, so a driver or database error can show hosts, collection names or
query details to the client.

- Every 500 answers JSON `{"error": "Internal server error"}`, whatever the error and whichever
  layer produced it (route mapping, final handler).
- The full error is logged at `ERROR` level with its traceback, the HTTP method and the path.
- This includes invalid stored data: the 500 of I01 no longer shows
  `Stored feed <{id}> is invalid: ...` to the client; that message goes only to the log.
- 4xx responses are unchanged: their messages describe the client's input and stay.

### MongoDB indexes (#23)
Today the `feeds` collection has only the `_id` index, so the listing, the front page and the
scraping deduplication scan the whole collection.

- The first migration (I07), `m0001_feeds_indexes`, creates these indexes on `feeds`:

| Name | Keys | Serves |
|---|---|---|
| `created_at_desc` | `createdAt: -1` | `/feed/list` (order by `created_at` desc) |
| `source_created_at_desc` | `source: 1, createdAt: -1` | `/feed/home` (filter by source, newest 10) |
| `source_title_created_at` | `source: 1, title: 1, createdAt: 1` | `exists_headline` (I02 dedupe) |

- None is unique: deduplication is by business day, not by exact instant (I02).
- The migration uses `create_indexes` with explicit names, which is idempotent as I07 requires.
- They are applied at startup like any migration (I07): once per database, before the app takes
  traffic, and a failure stops startup with exit code 1.
- Indexes are a storage detail: they are not part of the `FeedRepository` port.

### Test run without MongoDB fails fast (#24)
Today `uv run pytest` without a running MongoDB hangs: every Mongo test waits for the driver's
30-second server selection timeout, one after another.

- Tests connect to Mongo with a short server selection timeout (2 seconds). Production keeps the
  driver default.
- MongoDB reachability is checked **once** per test session, before the first test that needs it.
  If it does not answer, the session **fails** at once, locally and in CI alike, with
  `MongoDB is not reachable at <url>; start it with: docker compose up -d --wait mongo`. No test is
  ever skipped for a missing Mongo.
- The URL in that message hides credentials (only scheme, host, port and database).
- Every test that needs Mongo carries the `integration` marker, so `-m "not integration"` runs the
  rest of the suite without Mongo.
- Tests marked `network` keep running by default, locally and in CI: the app depends on those
  sites, and these tests are what detects a change in their markup.

## Unchanged
- Routes, success responses, 4xx status codes and messages (I01, or I06 if implemented).
- Feed documents and their fields (S01, I05).
- `FeedAlreadyExists` → 409 and `FeedNotFound` → 404, and the order of checks of each route, except
  that `PUT` no longer reads the stored feed before inserting (see edge cases).
- CI keeps running the full quality gate against a Mongo service container.

## Edge cases
- Two concurrent `PUT /feed/{id}` with the same id → exactly one 201 and one 409; the stored feed is
  the one from the 201.
- `PUT` with an id whose stored document is invalid (I01) → 409 (was 500): the existing document is
  no longer read.
- `PATCH` on a feed deleted between its `find` and its write → 404; the feed stays deleted.
- `PATCH` with no changes → still no write at all (S04), so it cannot race.
- A Mongo error on any route → 500 `{"error": "Internal server error"}`; the log has the original
  error.
- Starting the app on a database where `m0001_feeds_indexes` is applied → it does not run again.
- Indexes with the same keys but other options already present (created by hand) → the migration
  fails, startup fails with exit code 1 (I07); nothing is dropped automatically.
- `uv run pytest` with Mongo stopped → the session fails after one 2-second check, with the message
  above; nothing hangs and nothing is skipped.
- `uv run pytest -m "not integration"` with Mongo stopped → passes; Mongo is never contacted.

## Acceptance criteria
- Use-case tests with the fake: `FeedCreator` raises `FeedAlreadyExists` from `create` without a
  prior `find`; `FeedUpdater` raises `FeedNotFound` from `update`.
- Mongo repository integration tests: `create` on an existing id raises `FeedAlreadyExists` and
  keeps the original document; `update` on a missing id raises `FeedNotFound` and inserts nothing.
- Acceptance test: two concurrent `PUT` requests with the same id → one 201, one 409, and `GET`
  returns the first body.
- Error tests: an unexpected error and an `InvalidStoredFeed` both answer
  `{"error": "Internal server error"}`, and the captured log contains the original message, method
  and path.
- Migration integration test: after `m0001_feeds_indexes` runs, `feeds` has the three indexes with
  the names and keys above, and running it a second time does not fail (idempotency, I07).
- With Mongo unreachable, `uv run pytest` fails within a few seconds with the message above, and the
  URL in it shows no credentials. Verified by a test of the session check itself, not by stopping
  Mongo in CI.
- Every test that touches Mongo is marked `integration`: `-m "not integration"` passes with Mongo
  stopped.
- `network` tests still run in the default `uv run pytest`.
- `S01` (persistence foundation: "upsert by `_id`", 500 with `err.message`) and `I01` (500 body for
  invalid stored data) get a "Superseded by I08" note. `README.md` links I08 for #21–#24.
