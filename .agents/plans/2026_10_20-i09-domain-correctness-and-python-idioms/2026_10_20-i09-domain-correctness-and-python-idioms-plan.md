---
name: 'i09-domain-correctness-and-python-idioms'
description: 'Feeds keep their pending events, broken stored documents are always InvalidStoredFeed, the domain takes time from Clock, snake_case primitives, keyword-argument use cases, scrape naming, grouped domain modules and import-linter in the gate'
spec: 'specs/improvements/I09-domain-correctness-and-python-idioms.md'
branch: 'fix/i09-domain-correctness-and-python-idioms'
created_at: '2026-10-20T09:38:24Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-20T09:44:32Z'
---

# I09 · Domain correctness and Python idioms

## Goal

Resolve improvements #26–#31 without changing routes, OpenAPI, bodies, status codes, messages or
stored documents. The only observable change is the rename of the `SCRAP_*` environment variables
to `SCRAPE_*` (agreed, the project is not deployed).

## Context

- `Feed.update` uses `dataclasses.replace`, which rebuilds the aggregate through `__init__` and drops
  `_domain_events` (`init=False`). `test_feed.py` currently asserts that an updated feed has no
  events; that assertion changes. `ElMundoFeedScraper` calls `dataclasses.replace` on a feed that
  `extract_feeds` just created, losing its `FeedCreatedDomainEvent`. No scraper test checks events.
- `Feed.create`/`Feed.update` call `FeedCreatedAt.now()`/`FeedUpdatedAt.now()`, and
  `DomainEvent.occurred_on` defaults to `datetime.now(UTC)`. Only `FeedHomeSearcher` and
  `FeedHomeRefresher` use `Clock`. `SystemClock` is provided in `providers/infrastructure.py`;
  `FixedClock` exists in `tests/contexts/cms/shared/fakes/fixed_clock.py`. Several tests compare
  against the real clock with a 1 ms tolerance (`test_feed.py`, `test_feed_creator.py`,
  `test_front_page.py`, `test_date_time_value_object.py`, `test_home_feeds.py`).
- `_to_feed` catches only `InvalidArgumentError` behind `cast(FeedPrimitives, {"createdAt": None,
  **document})`. `RequiredStringValueObject` calls `.strip()` without a type check,
  `UuidValueObject` calls `fullmatch` without one, and `FeedSource` is a `StrEnum` that raises
  `ValueError`. Only `createdAt` is corrupted in the current repository tests.
- `FeedPrimitives` uses `createdAt`/`updatedAt`. `_STORAGE_FIELDS` maps them only for criteria;
  `MongoRepository._document`/`_with_id` map `id`↔`_id`. `InMemoryFeedRepository` mirrors the
  camelCase mapping. Gherkin datatables (`home-feed.feature`, `list-feed.feature`) use `createdAt`
  headers, read by `tests/apps/cms_backend/conftest.py`.
- `MongoDocument` is `dict[str, object]`.
- `FeedCreatorProps`/`FeedUpdaterProps` are `TypedDict`s; the routes pass dict literals.
  `main.py` installs `sys.excepthook` logging `"uncaughtException"`; nothing tests it.
- `scrap` appears in packages (`application/scrap`, `infrastructure/scrap`), `feed_scrap.py`
  (`FeedScrap.scrap()`), `ScrapMapping`, `scrap_front_page`, `FeedScraper._scrap_all`, settings
  `scrap_timeout_seconds`/`scrap_cooldown_seconds`, and in tests (`StubFeedScrap`,
  `BlockingFeedScrap`, `tests/scrap_fixtures.py`, `tests/fixtures/scrap/`, `test_scrap_feeds.py`,
  `scrap-feed.feature`, local variables). The route function `scrap_feeds` stays: FastAPI derives
  the operation id `scrap_feeds_feed_scrap_get` and the summary "Scrap Feeds" from it.
- Every `# noqa: E501` sits on a long `...persistence.mongo...` import; none on a `feeds` domain
  import. `pyproject.toml` declares `import-linter` (no contracts) and `hypothesis` (unused; it alone
  pulls `sortedcontainers`). CI runs ruff, ruff format, pyright, pytest; no `lint-imports`.
  `tests/test_architecture.py` checks `app.state` and dishka imports (including `tests/`); it stays.

### Agreed decisions

- Three phases (minimum granularity).
- The Mongo adapter reads the document through a local `Mapping[str, Any]` in `_to_feed`, with a
  comment: BSON values are known only at runtime and the value objects validate them. The shared
  `MongoDocument` type stays `dict[str, object]`.
- `Settings` fields become `scrape_timeout_seconds`/`scrape_cooldown_seconds`, read from
  `SCRAPE_TIMEOUT_SECONDS`/`SCRAPE_COOLDOWN_SECONDS`. The old names are not accepted.
- The "Internals changed by I09" notes on S02/S04/S06/S07 are dropped from I09: those specs name no
  internal `scrap` identifiers or camelCase primitives. `README.md` links I09 for #26–#31.
- `FeedSource._missing_` raises `InvalidArgumentError("<FeedSource> does not allow the value <x>")`;
  `Enum` propagates the exception, so `FeedSource(x)` stays the conversion.
- El Mundo trims through `ScrapeMapping.clean_description`, applied before `or None`, so a kicker
  that is only `.` still gives `null`.
- `FeedScraper` keeps its `timezone` for day bounds; the front-page scrapers get the `Clock`.

## Phase 1: Events survive and the domain takes time from `Clock` (#26, #28)

Derived feeds keep pending events, El Mundo creates each feed once, and every instant in the domain
comes from `Clock`.

### Public contracts

- `AggregateRoot`: a protected way for a derived aggregate to take over another's pending events,
  in order (e.g. `_keep_events_of(other: AggregateRoot) -> None`).
- `Feed.create(*, id, title, description, author, source, now: datetime) -> Feed`: `created_at`
  is `now` stored in UTC; `FeedCreatedDomainEvent.occurred_on` is `now`.
- `Feed.update(*, now: datetime, title: FeedTitle | None = None, description: FeedDescription |
  None = None) -> Feed | None`: `updated_at` is `now`; the result keeps the original's pending
  events. No `dataclasses.replace` on the aggregate.
- `DomainEvent.occurred_on: datetime` without default. `DateTimeValueObject.now()` removed.
- `FeedCreator(repository, event_bus, clock: Clock)`, `FeedUpdater(repository, clock: Clock)`
  (`execute` signatures unchanged in this phase).
- `ScrapMapping.clean_description: Callable[[str], str]` (default unchanged text).
- `scrap_front_page(client, mapping, clock: Clock)`, `extract_feeds(html, mapping, now: datetime)`.
- `ElMundoFeedScraper(client, clock)`, `ElEspanolFeedScraper(client, clock)`; `FeedsProvider`
  injects the shared `Clock`.

### Tests first

- [x] Domain: `Feed.update` on a feed with pending events returns a feed whose
      `pull_domain_events()` keeps them in order (replaces the "no events" assertion).
- [x] Domain: `Feed.update` with no changes returns `None` and records nothing.
- [x] Domain: `Feed.create(now=...)` with a non-UTC `now` stores it in UTC; the event's
      `occurred_on` equals `now`. `Feed.update(now=...)` sets `updated_at` to `now`.
- [x] Aggregate root: a derived aggregate keeps the source's events, followed by its own.
- [x] Use cases with `FixedClock`: `FeedCreator` stores `created_at` and publishes `occurred_on`
      equal to the clock's instant; `FeedUpdater` stores `updated_at` equal to it.
- [x] Scrapers: every El Mundo feed and every El Español feed has exactly one pending
      `FeedCreatedDomainEvent`; `created_at` equals the clock's instant.
- [x] El Mundo: a kicker ending in `.` loses the period; a kicker that is only `.` gives
      description `None` (existing tests stay green).
- [x] Shared: `DateTimeValueObject.now()` tests removed; `DomainEvent` without `occurred_on` is a
      type error (covered by pyright, no runtime test). Test events pass an explicit `occurred_on`.
- [x] Front page: `clean_description` runs before `or None` and each feed records one event.

### Implementation

- [x] Add the event carry-over to `AggregateRoot`; build the updated `Feed` explicitly in
      `Feed.update` and carry events.
- [x] Add `now` to `Feed.create`/`Feed.update`; drop `DateTimeValueObject.now()` and the
      `occurred_on` default.
- [x] Inject `Clock` into `FeedCreator`, `FeedUpdater` and both front-page scrapers; pass `now`
      through `scrap_front_page` → `extract_feeds`.
- [x] Add `clean_description` to `ScrapMapping`; remove `dataclasses.replace` from
      `ElMundoFeedScraper`.
- [x] Replace real-clock assertions with `FixedClock` in domain, use-case and scraper tests;
      replace `FeedCreatedAtMother.now()` with a fixed or random instant (acceptance seeding may
      keep `datetime.now(UTC)` in tests).
- [x] Wire the `Clock` in `providers/feeds.py`.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] Check `grep -rn "datetime.now" src/daily_trends_py/contexts` lists only `SystemClock` and the
      migration runner.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Storage names stay in the adapter and broken documents are `InvalidStoredFeed` (#29, #27)

The domain speaks snake_case; the Mongo adapter owns the only name mapping and turns every
document the domain rejects into `InvalidStoredFeed`.

### Public contracts

- `FeedPrimitives` keys: `id, title, description, author, source, created_at, updated_at`.
- `RequiredStringValueObject`, `StringValueObject` (non-`None`) and `UuidValueObject` reject a
  value that is not a `str` with `<Name> does not allow the value <value>`.
- `FeedSource(value)` with an unknown or non-string value raises `InvalidArgumentError` with
  `<FeedSource> does not allow the value <value>`.
- `MongoFeedRepository`: one mapping `id`↔`_id`, `created_at`↔`createdAt`, `updated_at`↔`updatedAt`
  used to write documents, read documents and translate criteria. `exists_headline` uses it too.
- `_to_feed`: reads each field with `.get` (missing → `None`), no `cast`, local `Mapping[str, Any]`
  with a justifying comment; raises `InvalidStoredFeed(stored_id, error)` for any
  `InvalidArgumentError`, and nothing else for a broken document.
- Stored documents and HTTP responses unchanged.

### Tests first

- [ ] Value objects: non-string title, author, description and id raise `InvalidArgumentError`
      with the existing format; unknown and non-string `source` too.
- [ ] Domain: primitives round trip uses snake_case keys in order.
- [ ] Repository (`integration`): documents with missing `title`, `author` or `source`, an unknown
      `source`, and a non-string `title` raise `InvalidStoredFeed` naming the id, from `find` and
      from `search`.
- [ ] Repository: a document without `updatedAt` reads as `updated_at` `None`.
- [ ] Repository: the raw stored document still has `_id`, `createdAt` and `updatedAt` (existing
      shape test stays green).
- [ ] App (`integration`): one broken-document case beyond `createdAt` answers the generic 500 and
      logs the reason (extend `test_invalid_stored_feed.py` parametrization).

### Implementation

- [ ] Add type checks to the shared string and UUID value objects; add `FeedSource._missing_`.
- [ ] Rename `FeedPrimitives` keys and update `to_primitives`/`from_primitives`.
- [ ] Move the name mapping into `MongoFeedRepository` for documents and criteria; replace
      `_STORAGE_FIELDS`; remove the `cast`.
- [ ] Simplify `InMemoryFeedRepository` (no camelCase mapping); map Gherkin `createdAt`/`updatedAt`
      headers in the acceptance seeding helper; update mothers and tests that seed raw documents.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Phase 3: Python idioms, module layout and dev tools (#30, #31)

Keyword-argument use cases, Python's default uncaught-exception handling, `scrape` naming, grouped
domain modules, import-linter in the gate, no `hypothesis`, and the docs.

### Public contracts

- `FeedCreator.execute(*, id: str, title: str, description: str | None, author: str, source:
  FeedSource) -> Feed`. `FeedCreatorProps` removed.
- `FeedChanges(TypedDict, total=False)`: `title: str`, `description: str | None`.
  `FeedUpdater.execute(id: str, **changes: Unpack[FeedChanges]) -> Feed`. `FeedUpdaterProps`
  removed. Routes call `creator.execute(id=..., ...)` and `updater.execute(id, **body)`.
- `main()`: no `sys.excepthook`, no `"uncaughtException"`; `SystemExit(3)` → 1 and
  `"Startup failed"` → 1 stay.
- Rename: `FeedScrape.scrape()` (module `feed_scrape.py`), `ScrapeMapping`, `scrape_front_page`,
  `FeedScraper._scrape_all`, packages `application/scrape` and `infrastructure/scrape` (and the
  mirrored test packages), `StubFeedScrape`, `BlockingFeedScrape`, `tests/scrape_fixtures.py`,
  `tests/fixtures/scrape/`. Route path `/feed/scrap`, function `scrap_feeds` (operation id and
  summary) and the `scrap-feed.feature` file stay.
- Settings: `scrape_timeout_seconds`/`scrape_cooldown_seconds`, env `SCRAPE_TIMEOUT_SECONDS`/
  `SCRAPE_COOLDOWN_SECONDS`.
- `feeds/domain` modules: `feed.py` (`Feed`, `FeedPrimitives`), `value_objects.py` (`FeedId`,
  `FeedTitle`, `FeedDescription`, `FeedAuthor`, `FeedSource`, `FeedCreatedAt`, `FeedUpdatedAt`),
  `errors.py` (`FeedAlreadyExists`, `FeedNotFound`), `events.py` (`FeedCreatedDomainEvent`);
  `feed_repository.py`, `feed_criteria.py`, `feed_scrape.py`, `find_feed.py` stay separate. Empty
  `__init__.py`.
- `[tool.importlinter]` in `pyproject.toml` (`root_package = "daily_trends_py"`,
  `include_external_packages = true`) with four forbidden contracts:
  domain ↛ application/infrastructure/apps; application ↛ infrastructure/apps;
  contexts ↛ fastapi/pydantic/dishka; domain and application ↛ pymongo/httpx.
- Quality gate: `... && uv run pyright && uv run lint-imports && uv run pytest` in `AGENTS.md`,
  `README.md`, CI and pre-commit. `hypothesis` removed from `pyproject.toml` and `uv.lock`.

### Tests first

- [ ] `FeedCreator` and `FeedUpdater` tests call `execute` with keyword arguments; `FeedUpdater`
      with `description=None` assigns `null`, with no changes keeps the feed and writes nothing.
- [ ] Settings: `SCRAPE_TIMEOUT_SECONDS`/`SCRAPE_COOLDOWN_SECONDS` are read and validated
      (existing settings tests renamed).
- [ ] `test_main.py`: existing startup-failure tests still exit with 1.
- [ ] OpenAPI test passes without changes to its expectations.
- [ ] `uv run lint-imports` passes; temporarily adding a forbidden import to a domain module makes
      it fail (manual check, not committed).

### Implementation

- [ ] Replace the `*Props` dicts with keyword arguments and `FeedChanges`; update routes and tests.
- [ ] Drop `_log_uncaught_exception` and the `sys.excepthook` assignment from `main.py`.
- [ ] Rename `scrap` → `scrape` in internal names, packages, test modules and fixtures with
      `git mv`; rename the settings and their env vars in `settings.py`, providers, `.env.example`,
      `README.md` and tests.
- [ ] Group the `feeds` domain modules; update every import; remove `# noqa: E501` where the new
      imports fit.
- [ ] Add the import-linter contracts; add `lint-imports` to `AGENTS.md`, `README.md`, CI and
      `.pre-commit-config.yaml`; `uv remove --dev hypothesis`.
- [ ] Docs: I04 gets a "Superseded by I09" note for the env var names; `README.md` improvements
      table already links I09 for #26–#31; set I09 status to done.
- [ ] Check `grep -rniE "scrap\b|scrap_|Scrap[A-Z]" src tests` matches only the `/feed/scrap` route,
      `scrap_feeds`, its OpenAPI metadata and the `scrap-feed.feature` contents.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` (with `lint-imports`) and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Run `/ai-project-implement-phase` for Phase 2.
