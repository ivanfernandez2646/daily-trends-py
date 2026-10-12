---
name: 'i06-idiomatic-fastapi-layer'
description: 'The HTTP layer uses Pydantic models, a DI container, global exception handlers and a generated OpenAPI document'
spec: 'specs/improvements/I06-idiomatic-fastapi-layer.md'
branch: 'fix/i06-idiomatic-fastapi-layer'
created_at: '2026-10-12T10:42:14Z'
updated_at: '2026-10-12T11:08:37Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I06 · Idiomatic FastAPI layer

## Goal

Resolve improvement #20. Requests and responses are described by Pydantic models. Use cases arrive
from a dishka DI container. Errors are translated by global exception handlers that map domain error kinds.
FastAPI generates the OpenAPI document. JavaScript-style value rendering disappears from the domain.
The repository stays green after each phase.

## Context

- There is no `contexts/cms/feeds/api` package. All transport code already lives in
  `src/daily_trends_py/apps/cms_backend/`:
  - `main.py`: `create_app`, the lifespan composition root, middleware, and the plain-text 500 handler
    at L57-59.
  - `routes/__init__.py`: router order is status, swagger, feed.
  - `routes/feed.py`: all feed routes, `_json_date` / `_feed_json` (L34-46), `LIST_CRITERIA` (L31).
  - `routes/status.py`, `routes/swagger.py`, `controllers.py` (`run_controller`), and `request_body.py`
    (`parse_body`, `MalformedRequestBody` → plain-text `Bad Request`).
- Use cases are stored one by one on `app.state` (`main.py` L68-93). Routes read them with
  `request.app.state.<name>` (`routes/feed.py` L51-145).
- Tests read `app.state.mongo_client` (`conftest.py`, `test_list_feeds.py`, `test_home_feeds.py`,
  `test_scrap_feeds.py`, `test_invalid_stored_feed.py`) and `app.state.feed_home_refresher`
  (`test_home_feeds.py`, `test_scrap_feeds.py`).
- `contexts/cms/shared/domain/raw_value.py` defines `MISSING` and `render_value`. These are used by
  `StringValueObject`, `RequiredStringValueObject`, `UuidValueObject` (`from_raw` and messages),
  `DateTimeValueObject`, `FeedUpdater` and `routes/feed.py`.
- `FeedCreatorProps` and `FeedUpdaterProps` type their values as `object`. `Feed.update` takes
  `None` to mean "keep the current value".
- `InvalidArgumentError` is the only shared error. `FeedNotFound`, `FeedAlreadyExists` and
  `InvalidStoredFeed` subclass `Exception` directly.
- `Criteria.__post_init__` raises `InvalidArgumentError`. Both criteria are module constants
  (`LIST_CRITERIA`, `HOME_CRITERIA`), so the change to `ValueError` cannot be seen over HTTP; only
  domain tests cover it.
- Stored documents still pass non-strings to the date value objects (`InvalidStoredFeed`, for example
  `<not-a-date>`), so the date value objects keep rendering arbitrary values.
- `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`. `docs/openapi.yml` is served at `/` and
  `/openapi.yml`, and the Dockerfile has `COPY docs ./docs` at L15.
- Tests mirror `src/`. App tests in `tests/apps/cms_backend/` use pytest-bdd `features/*.feature`
  and Python tests, carry the `integration` marker, and get `client` from `conftest.py`.
  `test_controllers.py` tests `run_controller`. `test_app.py` asserts the plain-text 500, Swagger at
  `/`, and that `/docs`, `/redoc` and `/openapi.json` return 404.

### Agreed decisions

- Three phases (intermediate granularity).
- `PUT` without a body behaves like `{}`: 400 `title: Field required; author: Field required`.
  `PATCH` without a body behaves like `{}`: 200, unchanged. The spec's "Request bodies" bullet
  already says so.
- Use cases are injected by a [dishka](https://dishka.readthedocs.io) DI container instead of the
  `FeedUseCases` dataclass and `Depends` providers. The spec and `specs/improvements/README.md` (#20)
  are updated. The container owns the resource lifecycle through generator providers. Neither `src/`
  nor `tests/` touches `app.state`; tests read the Mongo client and the refresher with
  `container.get(...)`.
- Without `render_value`, the date value objects render with `str()`. A missing stored `createdAt` now
  reads `<None>` (was `<null>`). `<not-a-date>` and `<1760000000000>` are unchanged.

## Phase 1: Error kinds and the DI container

Domain errors declare their kind, and one set of global handlers maps kinds to status codes with a
JSON body. A dishka container replaces the hand wiring in the lifespan, and routes receive use cases
from it. Bodies are still parsed by hand (`request_body.py` stays until Phase 2).

### Public contracts

- `contexts/cms/shared/domain/not_found_error.py`: `class NotFoundError(Exception)`.
- `contexts/cms/shared/domain/conflict_error.py`: `class ConflictError(Exception)`.
- `FeedNotFound(NotFoundError)` and `FeedAlreadyExists(ConflictError)`. Their messages do not change.
- `Criteria.__post_init__` raises `ValueError` with the same messages.
- `apps/cms_backend/errors.py`:

  ```python
  def register_exception_handlers(app: FastAPI) -> None: ...
  ```

  | Error | Status | Body |
  |---|---|---|
  | `InvalidArgumentError` and subclasses | 400 | `{"error": str(error)}` |
  | `NotFoundError` and subclasses | 404 | `{"error": str(error)}` |
  | `ConflictError` and subclasses | 409 | `{"error": str(error)}` |
  | Anything else (logged) | 500 | `{"error": str(error)}` |

  `MalformedRequestBody` keeps its plain-text 400 until Phase 2.
- Runtime dependency `dishka`, added with `uv add dishka`.
- `apps/cms_backend/container.py`, the composition root:

  ```python
  FEED_USE_CASES = (
      FeedCreator,
      FeedFinder,
      FeedSearcher,
      FeedUpdater,
      FeedDeleter,
      FeedScraper,
      FeedHomeSearcher,
  )


  class CmsBackendProvider(Provider):  # scope = Scope.APP
      # Settings comes from the container context.
      # Generator providers (closed in reverse order of creation):
      #   MongoClient (create_mongo_client / close), httpx.AsyncClient (timeout, User-Agent,
      #   redirects) / aclose, FeedHomeRefresher / aclose
      # Plain providers: EventBus (InMemoryEventBus), FeedRepository (MongoFeedRepository),
      #   Clock (SystemClock), FeedScraper (both scrapers) and the other use cases.
      def __init__(self, http_transport: httpx.AsyncBaseTransport | None) -> None: ...


  def create_container(
      settings: Settings,
      *overrides: Provider,
      http_transport: httpx.AsyncBaseTransport | None = None,
  ) -> AsyncContainer: ...
  ```

  `overrides` are providers declared with `override=True`; tests use them to swap fakes in.

  > **Deviation (agreed during Phase 1):** the HTTP transport is an argument, not an overridable
  > `httpx.AsyncBaseTransport` provider. Providing a transport in production would make httpx ignore
  > the proxy environment variables, so `None` keeps today's default.
- `apps/cms_backend/main.py`:
  - `create_app(container: AsyncContainer) -> FastAPI` (was `create_app(settings, http_transport)`).
    It calls `setup_dishka(container, app)`.
  - The lifespan resolves `FEED_USE_CASES` at startup, so an unreachable Mongo still fails startup.
    It calls `container.close()` on shutdown, and also when startup fails.
  - `main()` and `asgi.py` build the app as `create_app(create_container(Settings()))`.
- The feed router uses `APIRouter(route_class=DishkaRoute)`, and routes declare
  `finder: FromDishka[FeedFinder]` and so on.
- Nothing in `src/` or `tests/` reads or writes `app.state`.
- `controllers.py` (`run_controller`, `ErrorMapping`) is removed, and `GET /status` returns its `200`
  directly.

### Tests first

- [x] `tests/contexts/cms/feeds/domain/test_feed_errors.py`: `FeedNotFound` is a `NotFoundError`,
      `FeedAlreadyExists` is a `ConflictError`, and both messages are unchanged.
- [x] `tests/contexts/cms/shared/domain/test_criteria.py` and
      `tests/contexts/cms/feeds/domain/test_feed_criteria.py`: an invalid limit or field raises
      `ValueError` (not `InvalidArgumentError`).
- [x] `tests/apps/cms_backend/test_errors.py` (replaces `test_controllers.py`), on a throwaway app with
      `register_exception_handlers`:
  - a test-only subclass of each kind gives 400/404/409 with `{"error": msg}`;
  - an error of no kind, and an unexpected `ValueError`, give 500 JSON and are logged;
  - an error raised by a dependency is mapped too.
- [x] `tests/apps/cms_backend/test_app.py`: an unhandled error answers 500 `{"error": "boom"}` as
      JSON (was plain text) and is logged.
- [x] `tests/apps/cms_backend/test_container.py`:
  - every use case resolves from `create_container(settings)`, one instance per container;
  - closing the container closes the HTTP and Mongo clients. The order (refresher, then HTTP, then
    Mongo) follows from dishka finalizing in reverse order of creation: the refresher depends on
    both clients;
  - an override provider replaces `FeedRepository`;
  - the HTTP client uses the given transport and sends the `daily-trends-py` User-Agent.
- [x] `tests/apps/cms_backend/test_feed_router.py`: router tests through `TestClient`.
      `tests/apps/cms_backend/fakes_provider.py` (`FakesProvider`) supplies `InMemoryFeedRepository`
      and `RecordingEventBus`, so no Mongo is needed:
  - a feed is found from the injected repository;
  - `GET`/`DELETE`/`PATCH /feed/{missing}` → 404;
  - `PUT` on an existing id → 409;
  - an invalid UUID → 400 on every `/feed/{id}` method.
- [x] `tests/apps/cms_backend/test_main.py`: the existing startup and shutdown tests still pass,
      including an unreachable Mongo → exit 1.
- [x] `tests/test_architecture.py`:
  - no file in `src/` or `tests/` contains `app.state`;
  - no module outside `apps/cms_backend` (and its tests) imports `dishka`.
- [x] Adapt `conftest.py` and the home, list, scrap and invalid-stored-feed tests:
  - a `container` fixture builds `create_container(settings, http_transport=front_pages_transport)`;
  - `resolve(client, container, T)` and `resolve_mongo_client(...)` read app instances on the app
    loop;
  - a `raise_server_exceptions` fixture (default `True`) lets a module test 500s. FastAPI re-raises
    an error after its 500 handler answers.

### Implementation

- [x] Add `NotFoundError` and `ConflictError`, re-parent `FeedNotFound` and `FeedAlreadyExists`, and
      make `Criteria` raise `ValueError`.
- [x] Add `errors.py` and register it in `create_app`, replacing `_handle_unhandled_error`.
- [x] `uv add dishka`. Add `container.py`, and change `create_app` to take the container with a
      lifespan that resolves at startup and closes on shutdown. Update `main()` and `asgi.py`.
      dishka's `provide` import carries a justified `pyright: ignore` (its signature contains
      `Any`).
- [x] Rewrite the routes with `DishkaRoute` / `FromDishka`, without `run_controller`. Delete
      `controllers.py` and `test_controllers.py`.
- [x] `AGENTS.md`: replace "there is no DI container" with "wiring lives in one dishka container per
      app; only `apps/<app>` imports dishka".
- [x] Add "Superseded by I06" to the error table in `specs/feeds/S01-foundation.md` (map by kind,
      always JSON, no per-route lists).
- [x] Run the quality gate from `AGENTS.md` and fix failures. 364 tests pass. A smoke run of
      `daily-trends-py` against Mongo answers 200/404/400 and shuts down cleanly.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Typed requests

Pydantic models validate request bodies, validation errors answer 400 with the shared envelope, and
use cases receive typed props. `raw_value.py`, urlencoded bodies and the plain-text `Bad Request`
disappear.

### Public contracts

- `apps/cms_backend/routes/feed_schemas.py`:

  ```python
  class CreateFeedRequest(BaseModel):  # strict (no coercion), unknown fields ignored
      title: str
      author: str
      description: str | None = None


  @with_config(ConfigDict(strict=True))  # unknown fields ignored
  class UpdateFeedRequest(TypedDict):
      title: NotRequired[str]  # null is rejected
      description: NotRequired[str | None]  # absent ≠ null
  ```

  > **Decided under TDD:** `UpdateFeedRequest` is a `TypedDict` validated by Pydantic, not a
  > `BaseModel`. A model needs a sentinel default for "absent" (`str | MISSING`), and Pydantic then
  > reports `{"title": null}` as two union errors (`title.str`, `title.missing-sentinel`). With a
  > `TypedDict` an absent key is simply not there, `null` gives the single
  > `title: Input should be a valid string`, and the route passes it as `{"id": id, **body}`. The I06
  > spec is updated.
- Only `application/json` is accepted. A missing or empty body is read as `{}`: the feed router's
  route class, `routes/feed_route.py` (`FeedRoute(DishkaRoute)`), turns an empty body into a JSON
  `{}`. Otherwise FastAPI would answer `body: Field required` instead of listing each field.
- A `RequestValidationError` handler in `errors.py` answers 400 `{"error": "<loc>: <msg>; ..."}`:
  - `<loc>` is the dotted path without the `body` prefix.
  - A body-level problem (wrong content type, malformed JSON, a non-object value) uses `body`.
  - `<msg>` is Pydantic's message.
- `FeedCreatorProps = {id: str, title: str, description: str | None, author: str, source: FeedSource}`.
- `FeedUpdaterProps = {id: str, title: NotRequired[str], description: NotRequired[str | None]}`.
  An absent key keeps the value, and `description: None` assigns `null`.
- Order of checks: body schema (400) → id (400) → find (404) → blank title (400). For `PUT`: body
  schema → id → title → author → duplicate (409).
- Removed:
  - `contexts/cms/shared/domain/raw_value.py` (`MISSING`, `render_value`, `Missing`);
  - the `from_raw` methods on `StringValueObject`, `RequiredStringValueObject` and `UuidValueObject`
    (use cases call the constructors);
  - `apps/cms_backend/request_body.py`.
- Messages render values as they were sent: `<FeedTitle> is mandatory. Current value: <  >`,
  `<FeedId> does not allow the value <{id}>`. Date value objects use `str(value)`, so a missing stored
  `createdAt` gives `<None>`.

### Tests first

- [x] `tests/apps/cms_backend/test_feed_schemas.py`:
  - `CreateFeedRequest`:
    - title and author are required;
    - `0`, `true`, `[]` and `{}` are rejected for every string field;
    - a `null` or absent description is accepted;
    - unknown fields are ignored.
  - `UpdateFeedRequest`:
    - a `null` title is rejected;
    - `{}` stays `{}`, and `{"description": null}` stays `{"description": None}`;
    - `0`, `true`, `[]` and `{}` are rejected for both fields;
    - unknown fields are ignored.
- [x] `tests/apps/cms_backend/test_errors.py`:
  - a validation error gives 400 listing each problem by field
    (`title: Field required; author: Input should be a valid string`);
  - malformed JSON, a non-object value and an urlencoded body are reported at `body`.
- [x] `tests/apps/cms_backend/test_create_feed.py`. The `<undefined>`, `<null>`, `<true>`, `<a,b>`,
      urlencoded and plain-text `Bad Request` cases are replaced with the spec's edge cases:
  - no body, an empty JSON body and `{}` → `title: Field required; author: Field required`;
  - `{"title": 0}`, `{"title": null}` and `{"description": true}` → `<field>: Input should be a valid
    string`;
  - a blank title → `<FeedTitle> is mandatory. Current value: <  >`;
  - urlencoded, a JSON array or a JSON string → 400 at `body`;
  - malformed JSON → 400 JSON `body: JSON decode error`;
  - unknown fields, including `source`, are ignored.
- [x] `tests/apps/cms_backend/test_update_feed.py`:
  - `{"title": null}` and `{"title": 0}` → 400 `title: Input should be a valid string`;
  - `{"description": null}` → description `null`;
  - `{}` and no body → 200, unchanged;
  - `PATCH /feed/{missing}` with `{"title": 0}` → 400;
  - a blank title on a missing feed is still 404.
- [x] `tests/apps/cms_backend/test_feed_router.py`: `PATCH` with `{}` saves nothing, and
      `{"description": null}` clears only the description. These pass before the change too; they
      guard the behavior. The existing feed now has a fixed description, because the mother's random
      one can be `None`.
- [x] Domain and application tests:
  - delete `test_raw_value.py`;
  - `test_string_value_object.py` and `test_uuid_value_object.py` lose their `from_raw` / `MISSING`
    cases and keep the message cases with string values. There is no
    `test_required_string_value_object.py`: required strings are tested in
    `test_string_value_object.py`;
  - `test_date_time_value_object.py` and `test_mongo_feed_repository.py`: a missing stored date
    renders `<None>`;
  - `test_feed_creator.py` and `test_feed_updater.py` use typed props: an absent key keeps the value,
    and `description: None` assigns `null`.

### Implementation

- [x] Add `feed_schemas.py` with the two request schemas, the `RequestValidationError` handler in
      `errors.py`, and `FeedRoute`, which reads an empty body as `{}`.
- [x] Type `FeedCreatorProps` and `FeedUpdaterProps`. Make the use cases call the value-object
      constructors.
- [x] Remove `from_raw`, `raw_value.py` and `request_body.py` (and its handler in `main.py`), and
      switch the date value objects to `str(value)`.
- [x] Rewrite `PUT` and `PATCH` with the body schemas. `PATCH` passes `{"id": id, **body}`.
- [x] Add "Superseded by I06" to `S01` (urlencoded bodies), `S02` (value rendering, input,
      edge cases, malformed JSON) and `S04` (order of checks). Update the I06 spec for the
      `TypedDict`.
- [x] Run the quality gate from `AGENTS.md` and fix failures. 358 tests pass; the removed tests
      covered `render_value` and `from_raw`. A smoke run against Mongo answers a body-less `PUT`,
      a form body and malformed JSON as the spec says, and `PATCH` without a body leaves the feed
      unchanged.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Phase 3: Response models and generated OpenAPI

The feed JSON is a Pydantic model with snake_case keys and Pydantic's date format. Every route
declares its responses, and FastAPI generates and serves the OpenAPI document. The hand-written YAML
goes away.

### Public contracts

- `routes/feed_schemas.py`:

  ```python
  class FeedResponse(BaseModel):
      id: str
      title: str
      description: str | None
      author: str
      source: FeedSource
      created_at: datetime
      updated_at: datetime | None

      @classmethod
      def from_feed(cls, feed: Feed) -> Self: ...


  class ErrorResponse(BaseModel):
      error: str
  ```

  Dates look like `2026-10-12T08:00:00Z` or `2026-10-12T08:00:00.123000Z`. `_json_date` and
  `_feed_json` are removed. Mongo documents keep `createdAt` and `updatedAt`.
- Routes declare:
  - `response_model`: `FeedResponse` (`PUT` 201, `GET /feed/{id}`, `PATCH`), `list[FeedResponse]`
    (`/feed/list`, `/feed/home`, `/feed/scrap`), and none for `DELETE` 204;
  - `responses={...: {"model": ErrorResponse}}`: 400 on every route with a body or id; 404 on
    `GET`/`PATCH`/`DELETE /feed/{id}`; 409 on `PUT`; 500 on every feed route.
- `create_app` sets `FastAPI(title="Daily trends", version=<package version>, description=...)` with
  the default `/docs`, `/redoc` and `/openapi.json`. The document does not advertise FastAPI's 422.
- Removed: `routes/swagger.py`, `docs/openapi.yml`, and `COPY docs ./docs` in the Dockerfile.
  `GET /` and `GET /openapi.yml` answer 404.

### Tests first

- [ ] Success JSON has snake_case keys in the order `id, title, description, author, source,
      created_at, updated_at`, for `PUT`, `GET`, `PATCH`, `/feed/list`, `/feed/home` and
      `/feed/scrap`. Use the existing app tests, and the feature files' expected bodies where they
      list keys.
- [ ] Both date shapes appear: a seeded feed at a whole second gives no fraction, and a feed with
      milliseconds gives `.mmm000Z`.
- [ ] `tests/apps/cms_backend/test_app.py`:
  - `/docs` and `/redoc` → 200 HTML;
  - `/` and `/openapi.yml` → 404;
  - the gzip test uses `/openapi.json`.
- [ ] `tests/apps/cms_backend/test_openapi.py`:
  - title, version and description are set;
  - every route is listed;
  - `PUT`/`PATCH` reference `CreateFeedRequest`/`UpdateFeedRequest`;
  - success responses reference `FeedResponse`;
  - declared error responses reference `ErrorResponse`;
  - no 422 appears.

### Implementation

- [ ] Add `FeedResponse` and `ErrorResponse`, and declare `response_model` and `responses` on each
      route.
- [ ] Enable the generated docs with metadata and drop the 422 entries. Delete `swagger.py`,
      `docs/openapi.yml` and the Dockerfile `COPY docs`.
- [ ] Docs:
  - `AGENTS.md`: drop the `contexts/<context>/<subdomain>/api` layer; routers, schemas, the container
    and exception handlers live in `apps/<app>`.
  - `README.md`: the error contract (kinds → status, `{"error": ...}`, the validation message
    format), the generated OpenAPI (`/docs`, `/redoc`, `/openapi.json`), and the docker comment.
    Drop `feeds/api/` from the project layout.
- [ ] Add "Superseded by I06" to `S01` (Swagger from YAML) and `S02` (feed JSON keys and date format).
      Check that the `specs/improvements/README.md` row #20 links I06 (it does already).
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Review Phase 2, commit it with `/ai-project-conventional-commit`, then run `/ai-project-implement-phase` for Phase 3.
