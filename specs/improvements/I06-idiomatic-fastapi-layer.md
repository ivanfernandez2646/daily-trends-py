# I06 · Idiomatic FastAPI layer

**Status:** draft · **Fidelity:** intentional break with the ported behavior. Depends on S00–S07 and
I01–I05. Resolves improvement #20 from `README.md`.

## Goal
The HTTP layer uses FastAPI the way a Python developer expects: Pydantic models describe what goes
in and out, services arrive through typed dependencies, errors are translated by exception handlers,
and the OpenAPI document is generated from the code. Error messages stop imitating JavaScript. The
feed JSON follows Python conventions (snake_case keys, Pydantic's date format); there are no
clients yet, so nothing needs to stay compatible.

## Changes

### HTTP code stays in the app
- Transport lives in `apps/cms_backend`; the bounded context keeps only `domain`, `application` and
  `infrastructure`. There is no `api` package in the subdomain.
  - `routes/feed.py`: the feed router. `routes/feed_schemas.py`: its request and response schemas.
    `routes/status.py`: unchanged.
  - `container.py`: the dependency injection container (the wiring). `errors.py`: the exception
    handlers.
  - `main.py`: the app factory (container setup, lifespan, middleware, handler and router
    registration) and the process entry point.
- The fixed-routes-before-`/feed/{id}` rule (S01) still holds.

### Request bodies are Pydantic models
- `PUT /feed/{id}` body, `CreateFeedRequest`:
  - `title: str` (required), `author: str` (required), `description: str | None` (optional,
    default `None`).
- `PATCH /feed/{id}` body, `UpdateFeedRequest`, a `TypedDict` validated by Pydantic:
  - `title: NotRequired[str]` (`null` is rejected), `description: NotRequired[str | None]`.
  - "Absent" and `null` stay different for `description`: absent → not changed, `null` → assigned
    (S04). Only the fields the client sent reach the use case (see below).
  - A `TypedDict` rather than a `BaseModel`: an absent key is simply not there, so `null` is
    rejected with a single `title: Input should be a valid string`. A model needs a sentinel default
    for "absent", which Pydantic reports as a second union error.
- No type coercion: a number, boolean, list or object where a string is expected is rejected. Unknown
  fields are ignored.
- Only `application/json` bodies are accepted. A body with any other content type (urlencoded,
  `application/*+json`, none) → 400 `body: Content type should be application/json`. Malformed JSON
  or a JSON value that is not an object → 400. A missing or empty body is read as `{}`.
- These body rules live in one route class of the app, `JsonBodyRoute`, which acts only on routes
  that declare a body. Any router of any bounded context reuses it.
- The domain still validates what Pydantic cannot: a blank `title` or `author` →
  `<FeedTitle> is mandatory. Current value: <  >`, and an id that is not a valid UUID →
  `<FeedId> does not allow the value <{id}>`. These messages do not change.

### Request validation errors
- A request that fails schema validation → **400** (not FastAPI's default 422), body
  `{"error": "<message>"}`, the same envelope as every other error.
- `<message>` lists each problem as `<location>: <reason>`, joined with `; `. `<location>` is the
  dotted path without the `body` prefix (`title`, `author`); `<reason>` is Pydantic's message.
  Examples: `title: Field required`, `title: Input should be a valid string`.
- A body that is not a JSON object (wrong content type, malformed JSON, an array) has the location
  `body`.

### Values in domain messages
- `render_value` and its JavaScript rendering (`undefined`, `[object Object]`, `true`/`false`,
  lists joined with `,`) are removed. Only strings reach the value objects now, so a message shows
  the string as it was sent.
- The `MISSING` sentinel is removed too, so `raw_value.py` disappears. Use cases receive typed
  values (`str`, `str | None`) instead of `object`.
- "Absent" is expressed with `NotRequired` keys: `FeedUpdaterProps` is
  `{id: str, title: NotRequired[str], description: NotRequired[str | None]}`, and a key that was not
  sent is not in the dict. The route builds it from the validated `UpdateFeedRequest` and the id.
- The domain error messages keep their current wording with `<...>` around values.

### Responses are Pydantic models
- `FeedResponse` describes the feed JSON: `id`, `title`, `description`, `author`, `source`,
  `created_at`, `updated_at`, in that order.
  - Keys are **snake_case**, with no aliases: `createdAt` → `created_at`, `updatedAt` →
    `updated_at`.
  - Dates use Pydantic's default JSON format: ISO-8601 in UTC with `Z`, and a fractional part only
    when it is not zero, with six digits (`2026-10-12T08:00:00Z`, `2026-10-12T08:00:00.123000Z`).
    The custom `.000Z` formatting is removed.
  - The other values are unchanged.
- Only the HTTP JSON changes: Mongo documents keep their field names (`createdAt`, `updatedAt`).
- `ErrorResponse` describes `{"error": "<message>"}`.
- Every feed route declares its `response_model` (or none for `204`) and its error responses
  (`responses={404: {"model": ErrorResponse}, ...}`), so they appear in the OpenAPI document.

### Services through a dependency injection container
- Wiring moves to a [dishka](https://dishka.readthedocs.io) container composed in `container.py`, the
  composition root, from one provider per concern so a new bounded context only adds its own:
  - `InfrastructureProvider`, shared by every context: the Mongo client (which applies the
    migrations, I07), the HTTP client and its transport, the event bus and the clock.
  - `FeedsProvider`: the `FeedRepository` port, the scrapers, `FeedHomeRefresher` and the feed use
    cases (`FeedCreator`, `FeedFinder`, `FeedSearcher`, `FeedUpdater`, `FeedDeleter`, `FeedScraper`,
    `FeedHomeSearcher`).
  - Everything is `Scope.APP`: one instance per app.
- The container owns the lifecycle. Resources that need closing are generator providers: the
  refresher is closed first, then the HTTP client, then the Mongo client, as today.
- Startup and shutdown keep their behavior: the lifespan resolves `STARTUP_DEPENDENCIES` at startup
  and closes the container on shutdown. The list names the Mongo client explicitly, so an
  unreachable Mongo or a failing migration stops startup even when a test replaces the repository,
  plus each context's use cases.
- Routes receive use cases typed through the container (`finder: FromDishka[FeedFinder]` on a router
  with `route_class=DishkaRoute`). Neither the code nor the tests touch `app.state`.
- Tests replace a dependency with a test provider declared `override=True` (for example, an
  in-memory `FeedRepository` or the scrap fixtures' HTTP transport) and read resources with
  `container.get(...)`.
- Domain and application code stay unaware of the container: no dishka import outside
  `apps/cms_backend`.

### Errors through exception handlers
- `run_controller` and the per-route error lists are removed.
- The shared kernel (`contexts/cms/shared/domain`) defines the kinds of domain error, next to the
  existing `InvalidArgumentError`. They are domain concepts and know nothing about HTTP:
  - `NotFoundError`: the requested thing does not exist. `FeedNotFound` inherits from it.
  - `ConflictError`: the operation clashes with existing state. `FeedAlreadyExists` inherits from it.
- `errors.py` maps the **kinds**, not each concrete error, for every route. A new domain error picks
  its status by inheriting from a kind; the app does not change.

| Error | Status |
|---|---|
| Request validation error | 400 |
| `InvalidArgumentError` and subclasses | 400 |
| `NotFoundError` and subclasses | 404 |
| `ConflictError` and subclasses | 409 |
| Anything else (including `InvalidStoredFeed`) | 500 |

- An error that inherits from none of the kinds is a 500, on purpose: only domain errors that say
  what kind they are reach the client as a 4xx.

- Body `{"error": "<message>"}` for all of them, always JSON, built by one function. The plain-text
  `Bad Request` and the plain-text 500 of the final handler are gone.
- Errors the framework raises keep their status and use the same body: an unknown route → 404
  `{"error": "Not Found"}`, a method the route does not allow → 405 `{"error": "Method Not
  Allowed"}` (with its `Allow` header), a body that cannot be read → 400.
- The 500 is answered by a middleware inside CORS, so it carries the CORS headers like every other
  response, and the error is logged once.
- Invalid criteria (I05) must not become a 400 now that the mapping is global: building invalid
  `Criteria` raises `ValueError` instead of `InvalidArgumentError`, so it answers 500.

### Generated OpenAPI
- FastAPI generates the document at `GET /openapi.json`. `docs/openapi.yml`, `routes/swagger.py`
  (the `/` and `/openapi.yml` routes and the path arithmetic that locates the file) are removed; the
  Dockerfile stops copying `docs/`.
- FastAPI's defaults serve the docs: Swagger UI at `GET /docs`, ReDoc at `GET /redoc`. `GET /` is
  no longer a route and answers 404.
- The app sets the title, version and description of the document.

### Documentation
- `AGENTS.md` drops the `contexts/<context>/<subdomain>/api` layer from its architecture section:
  routers, Pydantic schemas, the container and exception handlers live in `apps/<app>`. "There is
  no DI container" becomes: wiring lives in one dishka container per app, and only `apps/<app>`
  imports dishka.
- `README.md` describes the new error contract and the generated OpenAPI document.

## Unchanged
- Routes, methods and success status codes. The feed JSON changes only in key case and date format.
- Status codes and messages of I01 for not found, conflict, invalid UUID, blank title or author.
- CORS, gzip, `/status`, startup and shutdown behavior, configuration (I04).
- Domain, use-case rules and persistence, other than the typed props and the removed rendering.

## Edge cases
- `PUT` without a body or with `{}` → 400 `title: Field required; author: Field required`.
- `PUT {"title": 0, "author": "a"}` → 400 `title: Input should be a valid string`.
- `PUT {"title": "  ", "author": "a"}` → 400 `<FeedTitle> is mandatory. Current value: <  >`.
- `PUT` with `Content-Type: application/x-www-form-urlencoded` or `application/merge-patch+json` →
  400 `body: Content type should be application/json`.
- `GET /` → 404 `{"error": "Not Found"}`; `POST /feed/list` → 405 `{"error": "Method Not Allowed"}`.
- A 500 to a request with an `Origin` header carries `Access-Control-Allow-Origin`.
- `PUT` with malformed JSON → 400 JSON body with location `body` (was plain text `Bad Request`).
- `PATCH {"title": null}` → 400 `title: Input should be a valid string` (was `<null>` in I01).
- `PATCH {"description": null}` → description set to `null`; `PATCH {}` → 200, unchanged.
- Order of checks changes: the body is validated before the feed is looked up, so
  `PATCH /feed/{missing-id}` with `{"title": 0}` → 400 (was 404). Then: id (400) → find (404) →
  blank title (400).
- `GET /feed/home` with an invalid stored feed → still 500 (I01).

## Acceptance criteria
- Router tests for each route through `TestClient`, with an override provider that supplies fakes
  (for example `InMemoryFeedRepository`) for the 4xx cases; Mongo-backed acceptance tests keep
  covering the full stack.
- Container tests: every use case resolves; resources close in order (refresher, HTTP client,
  Mongo); an unreachable Mongo still fails startup; migrations run at startup even when the
  repository is replaced by a fake.
- Schema tests: required fields, no coercion, `null` handling, absent vs `null` description,
  ignored unknown fields.
- Exception-handler tests: each row of the table → status and JSON body, using a test-only subclass
  of each kind (proves a new error needs no app change); an unexpected error → 500 JSON with CORS
  headers, logged once and not re-raised; framework errors (404, 405) use the same body.
- `FeedNotFound` is a `NotFoundError` and `FeedAlreadyExists` is a `ConflictError`.
- The `.feature` files and acceptance tests updated: `<undefined>` / `[object Object]` messages,
  urlencoded bodies and plain-text `Bad Request` replaced by the cases above.
- Tests assert the success JSON of `PUT`, `GET`, `PATCH`, `/feed/list`, `/feed/home` and
  `/feed/scrap`: snake_case keys in the order above, and both date shapes (with and without a
  fractional part).
- `GET /docs` and `GET /redoc` answer 200 HTML; `GET /` and `GET /openapi.yml` answer 404.
- A test asserts `/openapi.json` lists every route with its request schema, `FeedResponse` and the
  declared error responses.
- No `app.state` access in `src/` or `tests/`, and no dishka import outside `apps/cms_backend` (and
  its tests).
- `S01` (error table, urlencoded, Swagger from YAML), `S02` (value rendering, urlencoded, malformed
  JSON, feed JSON keys and date format) and `S04` (order of checks) get a "Superseded by I06" note. `README.md` links I06 for #20.
