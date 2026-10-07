---
name: 's02-create-and-find-feed'
description: 'Feed domain building blocks, PUT /feed/{id} to create a CMS feed and GET /feed/{id} to find it'
spec: 'specs/feeds/S02-create-and-find-feed.md'
branch: 'feat/s02-create-and-find-feed'
created_at: '2026-10-07T12:46:22Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-07T13:02:07Z'
implementation:
  - phase: 1
    status: 'done, committed'
    tool: 'Claude Code'
    model: 'claude-opus-5-5'
    finished_at: '2026-10-07T12:51:22Z'
  - phase: 2
    status: 'done, committed'
    tool: 'Claude Code'
    model: 'claude-opus-5-5'
    finished_at: '2026-10-07T12:57:49Z'
  - phase: 3
    status: 'done, pending review'
    tool: 'Claude Code'
    model: 'claude-opus-5-5'
    finished_at: '2026-10-07T13:02:07Z'
---

# S02 · Create and find a feed

## Goal

Create a CMS feed with `PUT /feed/{id}` and retrieve it with `GET /feed/{id}`, with the same status
codes, bodies and Mongo documents as the Node reference. The domain building blocks introduced here
(value objects, aggregate root, feed aggregate, repository port) are reused by S03–S07. The repository
stays green after every phase.

## Context

S01 delivered the app (`create_app`, lifespan with the Mongo client and `InMemoryEventBus` on
`app.state`), `run_controller` with per-route error mapping, `InvalidArgumentError`, `MongoRepository`
(`_persist`, `_by_id`, `_remove`) and the `DomainEvent` / `EventBus` ports. Behavior is ported from
`reference/daily-trends-node/src/contexts/cms/{feeds,shared}/domain/*`,
`.../feeds/application/{create,find}/*`, `.../feeds/infrastructure/persistence/mongo/MongoFeedRepository.ts`,
`.../apps/cms/backend/controllers/feeds/Feed{Creator,Finder}Controller.ts` and the
`create-feed.feature` / `find-feed.feature` files.

### Agreed decisions

- **Granularity:** intermediate, 3 phases (find end to end, create end to end, body edge cases).
- **Reference wins over spec text** for two discrepancies:
  - `FeedId` validates with the uuid@9 `validate` regex: versions 1–5 or the nil UUID
    (`/^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|00000000-0000-0000-0000-000000000000)$/i`).
    A v7 UUID is a 400. The spec's "any version" is corrected.
  - Date value-object errors read `<Function> doesn't allow the value <{value}>` (Node reads
    `this.constructor.name` inside a static method). The spec is corrected and the bug is added to
    `specs/improvements/`.
- **Non-string body values → 400 at the boundary** (documented divergence; Node answers 500
  `value.trim is not a function` for truthy non-strings and stores non-string descriptions raw):
  title/author → `<FeedX> is mandatory. Current value: <{js value}>`; description →
  `<FeedDescription> does not allow the value <{js value}>`.
- **Feed routes live in `apps/cms_backend/routes/feed.py`** next to `status.py`, reusing
  `run_controller`; S01 is not refactored.

### Smaller decisions

- **Malformed JSON body** → `PlainTextResponse("Bad Request", 400)` (divergence: Express answers an
  HTML 400 from its own final handler).
- **Body parsing** is an app-layer helper with no new dependency: `application/json` → JSON;
  `application/x-www-form-urlencoded` → `urllib.parse.parse_qs` with flat keys (one value → `str`, a
  repeated key → `list[str]`, which then fails as a non-string); any other content type → `{}`.
- **`undefined` vs `null`**: an absent field renders `<undefined>`, JSON `null` renders `<null>`.
- **Date parsing** uses `datetime.fromisoformat` in place of moment. In S02 dates only come from our
  own code or from Mongo, so no HTTP behavior changes.
- **Date storage**: date value objects hold the ISO-8601 string (UTC, milliseconds, `Z`, e.g.
  `2026-10-07T12:00:00.000Z`), as Node does, so Mongo documents stay identical.
- **Value-object equality** is dataclass equality (type and value). Node compares values only, across
  types; this is not observable.
- **Known Mongo difference kept from S01**: Node's `persist` writes `id: undefined`, which the driver
  stores as `id: null`; the port does not store `id`. Not revisited here.
- **Faker** is added as a dev dependency for Object Mothers (`MotherCreator`), as
  `ai-project-unit-testing` prescribes.

## Phases

## Phase 1: Find a feed end to end

Introduce the value objects, the `Feed` aggregate (primitives round trip), the feed errors, the
repository port with its Mongo adapter, the `FeedFinder` use case and `GET /feed/{id}`.

### Public contracts

- `daily_trends_py.contexts.cms.shared.domain.string_value_object`:
  `StringValueObject(value: str | None)` (frozen dataclass, accepts `None` and any string).
- `daily_trends_py.contexts.cms.shared.domain.required_string_value_object`:
  `RequiredStringValueObject(value: str)`; empty or whitespace-only →
  `InvalidArgumentError("<{ClassName}> is mandatory. Current value: <{value}>")`. Value not trimmed.
- `daily_trends_py.contexts.cms.shared.domain.uuid_value_object`: `UuidValueObject(RequiredStringValueObject)`;
  the uuid@9 check runs first → `InvalidArgumentError("<{ClassName}> does not allow the value <{value}>")`;
  `UuidValueObject.random()`.
- `daily_trends_py.contexts.cms.shared.domain.date_time_value_object`:
  `DateTimeValueObject(value: str | None)` (`None`/`""` valid) and
  `RequiredDateTimeValueObject(value: str)`; unparseable →
  `InvalidArgumentError("<Function> doesn't allow the value <{value}>")`; `now()` returns the current
  UTC instant as `YYYY-MM-DDTHH:MM:SS.mmmZ`.
- `daily_trends_py.contexts.cms.feeds.domain`:
  - `FeedId(UuidValueObject)`, `FeedTitle(RequiredStringValueObject)`,
    `FeedAuthor(RequiredStringValueObject)`, `FeedDescription(StringValueObject)`.
  - `FeedSource(StrEnum)`: `CMS`, `EL_PAIS`, `EL_MUNDO`.
  - `FeedPrimitives` (TypedDict): `id`, `title`, `description: str | None`, `author`, `source`,
    `createdAt`, `updatedAt: str | None`.
  - `Feed` (`@dataclass(eq=False)`): `id`, `title`, `description`, `author`, `source`, `created_at`,
    `updated_at`; `Feed.from_primitives(primitives) -> Feed`; `to_primitives() -> FeedPrimitives`
    (key order `id, title, description, author, source, createdAt, updatedAt`).
  - `FeedNotFound(Exception)`: `Feed with id <{id}> not found`.
  - `FeedRepository` Protocol: `async save(feed: Feed) -> None`, `async find(id: FeedId) -> Feed | None`.
  - `async find_feed(repository: FeedRepository, id: FeedId) -> Feed` raises `FeedNotFound`.
- `daily_trends_py.contexts.cms.feeds.application.find.feed_finder.FeedFinder(repository)`:
  `async execute(id: FeedId) -> Feed`.
- `daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository.MongoFeedRepository(MongoRepository, FeedRepository)`:
  collection `feeds`; `save` persists `to_primitives()`; `find` maps the document with
  `Feed.from_primitives`.
- Composition root: `create_app`'s lifespan builds `MongoFeedRepository` and `FeedFinder`, kept on
  `app.state`.
- HTTP: `GET /feed/{id}` → 200 feed JSON; `FeedNotFound` → 404 `{"error": "Feed with id <{id}> not found"}`;
  `InvalidArgumentError` → 400 `{"error": "<FeedId> does not allow the value <{id}>"}`.
- Dev dependency: `faker`.
- Test suites:
  - `tests/apps/cms_backend/features/find-feed.feature` (verbatim from the reference). Shared
    pytest-bdd steps (`I send a GET request to`, status code, `The response should be:`,
    `The response should contains:`, `There are feeds:`) move to `tests/apps/cms_backend/conftest.py`.
  - App tests use the test Mongo URL (`MONGO_URL`, default `mongodb://localhost:27017/daily-trends-test`)
    and clear the `feeds` collection before each test that touches it.
    *(Implementation: the `mongo_client` fixture moved to `tests/contexts/cms/conftest.py`, the test
    URL lives in `tests/mongo.py`, and the app `client` fixture clears `feeds` on start. BDD steps
    run async repository calls on the app's loop through `TestClient.portal`.)*
  - `tests/contexts/cms/shared/domain/` (`mother_creator.py`, value-object tests),
    `tests/contexts/cms/feeds/domain/` (Object Mothers: `feed_id_mother.py`, `feed_title_mother.py`,
    `feed_author_mother.py`, `feed_description_mother.py`, `feed_source_mother.py`, `feed_mother.py`),
    `tests/contexts/cms/feeds/fakes/in_memory_feed_repository.py`,
    `tests/contexts/cms/feeds/application/find/`,
    `tests/contexts/cms/feeds/infrastructure/persistence/mongo/` (marked `integration`).

### Tests first

- [x] `StringValueObject` accepts `None` and `""`; equal by value; different values (`"test"` vs `"TEST"`) are not equal.
- [x] `RequiredStringValueObject` rejects `""` and `"   "` with the exact mandatory message; keeps `" a "` untrimmed; equality.
- [x] `UuidValueObject` accepts v1–v5 and nil UUIDs; rejects a word, `""` and a v7 UUID with `<{ClassName}> does not allow the value <{value}>`; `random()` is valid; equality.
- [x] `DateTimeValueObject` accepts `None`, `""` and an ISO string; rejects a word with `<Function> doesn't allow the value <{value}>`.
- [x] `RequiredDateTimeValueObject` rejects `""` and a word with the same message; `now()` matches `YYYY-MM-DDTHH:MM:SS.mmmZ` and is UTC.
- [x] `FeedTitle`/`FeedAuthor` messages use their own class names; `FeedId` message uses `FeedId`.
- [x] `Feed.from_primitives(p).to_primitives() == p`, including `description: None` and `updatedAt: None`.
- [x] `FeedFinder` returns the stored feed; raises `FeedNotFound` with `Feed with id <{id}> not found` when missing (in-memory fake).
- [x] `integration`: `MongoFeedRepository.save` then `find` returns an equal feed (by primitives); the stored document is `{_id, title, description, author, source, createdAt, updatedAt}` with `null`s kept; `find` of a missing id → `None`.
- [x] `integration`: `find-feed.feature` — existing feed → 200 containing the feed; missing → 404 with the exact error.
- [x] `integration`: `GET /feed/not-a-uuid` → 400 `{"error": "<FeedId> does not allow the value <not-a-uuid>"}`.

### Implementation

- [x] Add `faker` as a dev dependency with `uv add --dev faker`.
- [x] Implement the shared value objects, the feed domain, `FeedFinder` and `MongoFeedRepository`.
- [x] Add `routes/feed.py` with `GET /feed/{id}` (declares `FeedNotFound` → 404, `InvalidArgumentError` → 400) and register it in `register_routes`.
- [x] Wire the repository and `FeedFinder` in `create_app`'s lifespan.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Phase 2: Create a feed end to end

Add the aggregate root with event recording, `feed.created`, `Feed.create`, the `FeedCreator` use case,
JSON body parsing and `PUT /feed/{id}`.

### Public contracts

- `daily_trends_py.contexts.cms.shared.domain.aggregate_root.AggregateRoot`:
  `record(event: DomainEvent) -> None`, `pull_domain_events() -> list[DomainEvent]` (returns and clears).
  `Feed` extends it.
- `daily_trends_py.contexts.cms.feeds.domain`:
  - `FeedCreatedDomainEvent(DomainEvent)`: `event_name = "feed.created"`, `title: str`.
  - `Feed.create(id, title, description, author, source) -> Feed`: `created_at = RequiredDateTimeValueObject.now()`,
    `updated_at = DateTimeValueObject(None)`, records `FeedCreatedDomainEvent(aggregate_id=id, title=title)`.
  - `FeedAlreadyExists(Exception)`: `Feed with id <{id}> already exists`.
- `daily_trends_py.contexts.cms.feeds.application.create.feed_creator`:
  - `FeedCreatorProps` (TypedDict): `id: str`, `title: str`, `description: str | None`, `author: str`,
    `source: FeedSource`.
  - `FeedCreator(repository, event_bus)`: `async execute(props) -> Feed`. Validates id, title,
    description, author in that order (first failure wins); an existing id → `FeedAlreadyExists`
    with nothing saved; otherwise saves, then publishes the pulled events.
- `daily_trends_py.apps.cms_backend.request_body.parse_body(request: Request) -> Mapping[str, object]`:
  JSON bodies only in this phase; any non-JSON content type, an empty body or a non-object JSON → `{}`.
  *(Until Phase 3 the route casts raw body values to the `str` props; a missing or non-string
  title or author answers 500.)*
- HTTP: `PUT /feed/{id}` with `title`, `description` (optional, missing → `null`), `author`; `source`
  is always `CMS`. 201 with the feed JSON (`updatedAt: null`); `FeedAlreadyExists` → 302
  `{"error": "Feed with id <{id}> already exists"}` without `Location`; `InvalidArgumentError` → 400.
- Composition root: `FeedCreator` built in the lifespan with the shared event bus.
- Test suites: `tests/apps/cms_backend/features/create-feed.feature` (verbatim) with a
  `I send a PUT request to "…" with body:` step; `tests/contexts/cms/shared/fakes/recording_event_bus.py`;
  *(Dropped during implementation: `feed_created_domain_event_mother.py`. The event has a random id
  and date, so tests assert its name, aggregate id and title directly.)*
  `tests/contexts/cms/feeds/application/create/`.

### Tests first

- [x] `AggregateRoot.pull_domain_events` returns recorded events in order and a second pull returns `[]`.
- [x] `Feed.create` sets `updated_at` to `None`, `created_at` to now, and records one `FeedCreatedDomainEvent` with the feed id and title.
- [x] `FeedCreator` saves the feed with `updatedAt: None` and returns it.
- [x] `FeedCreator` publishes `feed.created` with the feed id and title.
- [x] `FeedCreator` raises `FeedAlreadyExists` when the id exists; nothing is saved and nothing is published.
- [x] `FeedCreator` raises the first validation failure in order id → title → description → author.
- [x] `integration`: `create-feed.feature` — new id → 201 containing the feed; existing id → 302 with the exact error.
- [x] `integration`: the same id twice in a row → 201 then 302, no `Location` header; the stored feed is unchanged.
- [x] `integration`: `PUT` without `description` → 201 with `"description": null`; a `source` in the body is ignored (`CMS`).
- [x] `integration`: `PUT /feed/not-a-uuid` → 400 `<FeedId> does not allow the value <not-a-uuid>`; blank title → 400 mandatory message.

### Implementation

- [x] Implement `AggregateRoot`, `FeedCreatedDomainEvent`, `Feed.create`, `FeedAlreadyExists` and `FeedCreator`.
- [x] Add `parse_body` (JSON only) and `PUT /feed/{id}` in `routes/feed.py`, keeping fixed `/feed/*` routes before `/feed/{id}`.
- [x] Wire `FeedCreator` in `create_app`'s lifespan.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Phase 3: Body edge cases

Accept raw body values in the create path so missing, `null`, non-string, urlencoded and malformed
bodies answer as agreed, and record the divergences in the specs.

### Public contracts

- *(Renamed during implementation to keep JS references out of the code: `js_value` →
  `raw_value`, `js_string` → `render_value`.)*
- `daily_trends_py.contexts.cms.shared.domain.js_value`: `MISSING` sentinel (an absent field) and
  `js_string(value: object) -> str` rendering as JS `String()` does for the cases we hit (`MISSING` →
  `undefined`, `None` → `null`, `True`/`False` → `true`/`false`, integral floats without `.0`, lists
  joined with `,`, dicts → `[object Object]`, strings as is).
- Value objects gain raw-input factories used by the create path:
  `RequiredStringValueObject.from_raw(value: object)` (non-string or blank → mandatory message),
  `StringValueObject.from_raw(value: object)` (`MISSING`/`None` → `None`; non-string →
  `<{ClassName}> does not allow the value <{js value}>`), `UuidValueObject.from_raw(value: object)`.
- `FeedCreatorProps` fields `id`, `title`, `description`, `author` become `object` (raw body values,
  `MISSING` when absent).
- *(Implementation: `parse_body` runs before `run_controller` and raises `MalformedRequestBody`, which
  an app exception handler turns into the plain-text 400. A JSON body that does not start with `{` or
  `[` (e.g. `"a title"`, `123`) is also malformed.)*
- `parse_body`: adds `application/x-www-form-urlencoded` (flat keys; repeated key → `list[str]`);
  malformed JSON → `PlainTextResponse("Bad Request", 400)`; a JSON body that is not an object (e.g.
  an array) behaves as having no fields.
- Spec updates: `specs/feeds/S02-create-and-find-feed.md` (uuid@9 versions, `<Function>` date
  messages, non-string and malformed-JSON divergences, urlencoded support) and a new row in
  `specs/improvements/README.md` for the `<Function>` date-message bug.

### Tests first

- [x] `js_string` renders `MISSING`, `None`, booleans, integers, integral and non-integral floats, lists and dicts as JS does.
- [x] `from_raw` factories: valid strings pass; `MISSING`, `None`, numbers and booleans fail with the agreed messages and class names.
- [x] `FeedCreator` with a missing title → `<FeedTitle> is mandatory. Current value: <undefined>`; `null` title → `<null>`; missing description → `None`.
- [x] `integration`: `PUT` with no body → 400 `{"error": "<FeedTitle> is mandatory. Current value: <undefined>"}`.
- [x] `integration`: `PUT` with `"title": 123` → 400 `<FeedTitle> is mandatory. Current value: <123>`; `"description": true` → 400 `<FeedDescription> does not allow the value <true>`.
- [x] `integration`: urlencoded `title=…&author=…` → 201; a repeated `title` key → 400.
- [x] `integration`: malformed JSON → 400 plain text `Bad Request`.

### Implementation

- [x] Implement `js_value`, the `from_raw` factories and raw `FeedCreatorProps`.
- [x] Extend `parse_body` for urlencoded and malformed JSON.
- [x] Update the S02 spec and `specs/improvements/README.md`.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Next step

All S02 phases are implemented; Phase 3 awaits review (and an optional `/ai-project-conventional-commit`).
Then push the branch, open a PR, and plan S03 with
`/ai-project-create-plan specs/feeds/S03-list-feeds.md`.
