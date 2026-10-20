# I09 · Domain correctness and Python idioms

**Status:** draft · **Fidelity:** no observable change except the `SCRAPE_*` environment
variables (see #30). Routes, OpenAPI, request and response bodies, status codes, messages and
stored documents stay exactly as they are. Depends on S00–S07,
I01–I08 (the 500 body for invalid stored data is the generic one from I08). Resolves improvements
#26–#31 from `README.md`.

## Goal
Every feed keeps the domain events it records. Every stored document the domain cannot read is
reported as invalid stored data. The domain takes time from the `Clock` port only. The internals
read like ordinary Python: snake_case in the domain, keyword arguments in use cases, related types
grouped in one module, the correct English verb, and dev tools that are either used or removed.
The external contract still matches the original project.

## Changes

### Domain events survive derived feeds (#26)
Today `dataclasses.replace` builds a new `Feed` through `__init__`, and `_domain_events`
(`init=False`) starts empty again. The El Mundo scraper trims the description of a feed it has
just created, so the `FeedCreatedDomainEvent` recorded by `Feed.create` is lost. The El Español
scraper keeps it. `Feed.update` would drop any pending event the same way.

- A feed made from another one (`Feed.update`, or any other copy the domain offers) keeps the
  original's pending events, in order, followed by any event it records.
- The El Mundo scraper trims the description before `Feed.create`, so each scraped feed is created
  once and records exactly one `FeedCreatedDomainEvent`, as El Español feeds do.
- No infrastructure code calls `dataclasses.replace` on an aggregate.

### Invalid stored documents are always `InvalidStoredFeed` (#27)
Today `_to_feed` catches only `InvalidArgumentError`, and `cast(FeedPrimitives, ...)` hides what
the document really holds. A missing `title`, `author` or `source` raises `KeyError`, an unknown
`source` raises `ValueError`, and a `title` that is not a string raises `AttributeError`.

- The Mongo adapter reads each field without assuming it is there. A missing field is treated as
  `None`, as `createdAt` already is.
- Value objects reject a value of the wrong type with `InvalidArgumentError`, using the message
  format they already use (`<FeedTitle> does not allow the value <...>`). `FeedSource` rejects an
  unknown value the same way.
- Any document the domain rejects raises `InvalidStoredFeed` with the stored id and the reason.
  `InvalidStoredFeed` is the only error a broken document can raise from the repository.
- The `cast` is removed: the adapter builds the primitives from the document's real values. It
  reads them through a local `Mapping[str, Any]`, justified in a comment: BSON values are known only
  at runtime, and the value objects validate them. The shared `MongoDocument` type is unchanged.

### The domain takes time from `Clock` (#28)
Today `FeedHomeSearcher` and `FeedHomeRefresher` use `Clock`, while `DateTimeValueObject.now()`
and `DomainEvent.occurred_on` call `datetime.now(UTC)`. Tests cannot fix `created_at`,
`updated_at` or `occurred_on`.

- `Feed.create` and `Feed.update` receive the current instant as a keyword argument `now`. The
  feed stores it, converted to UTC as today, and the events it records use it as `occurred_on`.
- `DomainEvent.occurred_on` has no default. `DateTimeValueObject.now()` is removed.
- `FeedCreator` and `FeedUpdater` receive a `Clock`. The scrapers receive the same `Clock` through
  the composition root.
- `SystemClock` stays the only place in `contexts` that reads the system time. The migration runner
  keeps its own timestamps: they are infrastructure bookkeeping, not domain data.

### Storage names stay in the storage adapter (#29)
Today `FeedPrimitives` uses `createdAt` and `updatedAt`, the MongoDB field names, inside the
domain. `_STORAGE_FIELDS` maps `created_at` to `createdAt` only for criteria.

- `FeedPrimitives` uses `id`, `created_at` and `updated_at`.
- The Mongo adapter owns one mapping between domain names and document fields (`id` ↔ `_id`,
  `created_at` ↔ `createdAt`, `updated_at` ↔ `updatedAt`). It uses that mapping for documents and
  for criteria alike.
- Stored documents keep the same field names. The HTTP response keeps `createdAt` and
  `updatedAt`.

### Python idioms in use cases, entry point and naming (#30)
Today the code keeps habits from the original project that read oddly in Python.

- **Keyword arguments.** Use cases take keyword arguments instead of a `*Props` `TypedDict`:
  `FeedCreator.execute(*, id, title, description, author, source)`. `FeedUpdater` must still tell an
  absent field from `None`, so it takes `execute(id, **changes: Unpack[FeedChanges])`, where
  `FeedChanges` is a `TypedDict(total=False)` with `title` and `description`. Use cases stay
  classes with `execute`, because the container injects their dependencies.
- **Entry point.** `main` drops the custom `sys.excepthook` and the `"uncaughtException"` log.
  An uncaught exception still ends the process with exit code 1 and its traceback on stderr, which
  is Python's default. The `SystemExit(3)` to 1 mapping stays: startup failures exit with code 1
  (S01, I04, I07).
- **`scrape`, not `scrap`.** Internal names use the English verb: `FeedScraper.scrape()`, the
  `FeedScrape` port (renamed from `FeedScrap`), `ScrapeMapping`, `scrape_front_page`, and the
  `application/scrape` and `infrastructure/scrape` packages. The route `/feed/scrap`, its OpenAPI
  operation id and summary (derived from the route function `scrap_feeds`, which keeps its name),
  the `scrap-feed.feature` file and the spec titles stay unchanged.
- **Settings.** `scrap_timeout_seconds` and `scrap_cooldown_seconds` become
  `scrape_timeout_seconds` and `scrape_cooldown_seconds`, read from `SCRAPE_TIMEOUT_SECONDS` and
  `SCRAPE_COOLDOWN_SECONDS`. The project is not deployed, so the `SCRAP_*` names (I04) are not kept
  as aliases. This is the only observable change in I09.

### Module layout and dev tools (#31)
Today each value object and error lives in its own module, often a 3-line subclass, so a use case
imports from many modules. `pyproject.toml` declares `import-linter` and `hypothesis`, but
neither is used.

- `feeds/domain` groups related types:
  - `feed.py`: `Feed` and `FeedPrimitives`.
  - `value_objects.py`: `FeedId`, `FeedTitle`, `FeedDescription`, `FeedAuthor`, `FeedSource`,
    `FeedCreatedAt` and `FeedUpdatedAt`.
  - `errors.py`: `FeedAlreadyExists` and `FeedNotFound`.
  - `events.py`: `FeedCreatedDomainEvent`.
  - The repository port, criteria, scrape port and `find_feed` keep their own modules.
- `contexts/cms/shared` keeps its layout. This spec only groups the `feeds` domain.
- Packages re-export nothing (empty `__init__.py`, as today). Imports name the new modules.
- `import-linter` gets contracts for the rules in `AGENTS.md`:
  - `domain` imports neither `application`, `infrastructure` nor `apps`.
  - `application` imports neither `infrastructure` nor `apps`.
  - `contexts` imports neither `fastapi`, `pydantic` nor `dishka`.
  - `domain` and `application` import neither `pymongo` nor `httpx`.

  `uv run lint-imports` joins the quality gate in `AGENTS.md` and CI.
- `hypothesis` is removed from the dev dependencies.

## Unchanged
- Every route, method, status code, message, request body and response body (I01, I06, I08).
- The generated OpenAPI document.
- MongoDB documents, field names, indexes and migrations (S01, I05, I07, I08).
- Scraping results: same feeds, same descriptions (El Mundo still drops one trailing period), same
  deduplication (I02).
- Exit codes: 1 for startup failures and for uncaught exceptions.
- Every other setting and environment variable (I04).
- The event bus and its lack of subscribers (README #13).

## Edge cases
- An El Mundo feed whose kicker ends in `.` → description without the period, exactly one
  `FeedCreatedDomainEvent` pending.
- An El Mundo feed whose kicker is only `.` → description `null`, as today.
- `Feed.update` with no changes → `None`, no new event, no write (S04).
- `Feed.update` on a feed that has pending events → the result keeps them, in order.
- Stored documents with a missing `title`, `author` or `source`, an unknown `source`, or a
  non-string `title` → `InvalidStoredFeed` naming the id. The client receives the generic 500
  (I08), and the log shows the reason.
- A stored document without `updatedAt` → `updated_at` is `None`, as today. It is not invalid.
- `PATCH` with `{"description": null}` → assigns `null`. `PATCH` with `{}` → no change (S04,
  I01).
- A `Clock` in a non-UTC business timezone → `created_at` and `updated_at` are stored in UTC, as
  today.

## Acceptance criteria
- Scraper test: every feed from the El Mundo scraper has exactly one pending
  `FeedCreatedDomainEvent`, and so does every feed from El Español.
- Domain test: `Feed.update` keeps pending events from the original feed.
- Repository integration tests: each broken document listed in the edge cases raises
  `InvalidStoredFeed` from `find` and from `search`.
- Value object tests: wrong types and an unknown source raise `InvalidArgumentError` with the
  existing message format.
- Use-case tests use a fixed clock. `created_at`, `updated_at` and the event's `occurred_on` equal
  its instant.
- `grep -rn "datetime.now" src/daily_trends_py/contexts` lists only `SystemClock` and the
  migration runner.
- `FeedPrimitives` has no camelCase keys. The repository tests still find `createdAt` and
  `updatedAt` in the raw stored documents.
- `main.py` has no `excepthook` and no `uncaughtException`. A test still checks that a startup
  failure exits with code 1.
- `grep -rni "scrap\b\|scrap_\|Scrap[A-Z]" src tests` matches only the `/feed/scrap` route, its
  function `scrap_feeds` and the OpenAPI metadata and feature file that name them.
- Settings tests read `SCRAPE_TIMEOUT_SECONDS` and `SCRAPE_COOLDOWN_SECONDS`. `.env.example` and
  `README.md` name them, and I04 gets a "Superseded by I09" note.
- The OpenAPI test passes without changes to its expected document.
- `uv run lint-imports` passes and runs in CI. `hypothesis` is no longer in `pyproject.toml` or
  `uv.lock`.
- Every existing acceptance test passes without changes to its requests, expected responses or
  expected stored documents. Only imports and seeding helpers change.
- `README.md` links I09 for #26–#31. The feature specs need no note: none of them names the
  renamed internals or the primitives' keys.
