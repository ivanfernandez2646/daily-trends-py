---
name: 's01-foundation'
description: 'Running FastAPI app with settings, Mongo connection, GET /status, per-route error mapping, event bus and Docker/CI delivery'
spec: 'specs/feeds/S01-foundation.md'
branch: 'feat/s01-foundation'
created_at: '2026-10-07T11:47:34Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-07T12:04:35Z'
implementation:
  - phase: 1
    status: 'done, committed'
    tool: 'Claude Code'
    model: 'claude-opus-5-5'
    finished_at: '2026-10-07T11:53:45Z'
  - phase: 2
    status: 'done, pending review'
    tool: 'Claude Code'
    model: 'claude-opus-5-5'
    finished_at: '2026-10-07T12:04:35Z'
---

# S01 · Foundation

## Goal

A running app that starts, reads configuration, connects to Mongo, answers `GET /status` and
formats errors the way every later capability (S02–S07) expects. The repository stays green after
every phase.

## Context

The Python side is a bare `uv` project (`src/daily_trends_py/__init__.py` with a `main()` stub); there
is no tool configuration (ruff, pyright strict, pytest) and no tests yet. Behavior is ported from
`reference/daily-trends-node/src/apps/cms/backend/*`, `.../controllers/Controller.ts`,
`.../shared/infrastructure/persistence/mongo/*` and `.../eventBus/inMemory/*`.

### Agreed decisions

- **Granularity:** intermediate, 4 phases.
- **Layout:** `src/daily_trends_py/contexts/cms/{feeds,shared}/…` (context `cms`, subdomain `feeds`),
  app at `src/daily_trends_py/apps/cms_backend/`. README and AGENTS.md are updated to match.
- **Feed errors:** `FeedNotFound` / `FeedAlreadyExists` arrive in S02 with `FeedId`. S01 tests the
  mapping mechanism for 400 (`InvalidArgumentError`) and for 404/302/500 with test-only error classes.
- **Mongo tests:** real Mongo at `MONGO_URL`, tests marked `integration`. Locally
  `docker compose up -d mongo`; CI provides a Mongo service. Plain `uv run pytest` needs Mongo running.

### Discrepancies resolved against the reference

- **Final handler body is plain text.** Node does `res.status(500).send(err.message)`; the port returns
  `PlainTextResponse(str(exc), 500)`, not `{"error": …}`.
- **"Thrown non-Error value → 500" is not applicable.** Python can only raise `BaseException`
  subclasses. The criterion is dropped; non-`Exception` `BaseException`s (e.g. `KeyboardInterrupt`)
  propagate.
- **Swagger.** Node mounts Swagger UI at `/` from `docs/openapi.yml`. The port copies the file to
  `docs/openapi.yml`, serves the UI at `GET /` and the file at `GET /openapi.yml`, and disables
  FastAPI's `/docs`, `/redoc` and `/openapi.json`.
- **Env variable** is `ENV` (spec), not `NODE_ENV` (Node). `dev.json`/`test.json` are not ported
  (improvement #1).
- **Body parsing** (JSON + urlencoded) is deferred to S02, where `PUT /feed/{id}` is the first route
  that reads a body. It will be a helper in the app layer, with no new dependency.
- **Unknown routes** keep FastAPI's default 404 (`{"detail":"Not Found"}`); Express's HTML 404 is not
  covered by any spec or `.feature`.
- **Compression** uses `GZipMiddleware(minimum_size=1024)` to match Express `compression`'s threshold.
  **CORS** uses `CORSMiddleware(allow_origins=["*"], allow_methods=["GET","HEAD","PUT","PATCH","POST","DELETE"])`,
  matching `cors()` defaults.
- **Route order rule** (fixed `/feed/*` routes before `/feed/{id}`) has no routes to apply to yet; it
  is recorded as a docstring rule on the router-registration function and enforced by S02/S03/S06/S07.

## Phases

## Phase 1: Tooling, settings, app and `GET /status`

Set up tool configuration and the layout, load settings, build the app in one composition root, and
expose `GET /status` plus a runnable entrypoint.

### Public contracts

- `pyproject.toml`: `[tool.ruff]`, `[tool.pyright]` (`typeCheckingMode = "strict"`),
  `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `markers = ["integration: needs MongoDB"]`),
  `[tool.fastapi] entrypoint = "daily_trends_py.apps.cms_backend.asgi:app"`;
  `[project.scripts] daily-trends-py = "daily_trends_py.apps.cms_backend.main:main"`.
- `daily_trends_py.apps.cms_backend.settings.Settings` (pydantic-settings):
  `env: Literal["production", "dev", "test"] = "dev"` (env `ENV`),
  `mongo_url: str = "mongodb://localhost:27017/daily-trends"` (env `MONGO_URL`),
  `port: int = 5000` (env `PORT`).
- `daily_trends_py.apps.cms_backend.main.create_app(settings: Settings) -> FastAPI`.
- `daily_trends_py.apps.cms_backend.asgi.app` for `fastapi dev`. *(Changed during implementation: a
  module-level `app` in `main.py` built `Settings` at import, so invalid configuration escaped
  `main()`'s startup handler.)*
- `daily_trends_py.apps.cms_backend.main.main() -> None`: runs uvicorn on `0.0.0.0:settings.port`;
  a startup error is logged and the process exits with code 1 (uvicorn's own startup-failure exit
  code 3 is translated to 1); `sys.excepthook` logs uncaught exceptions and the interpreter exits
  with code 1.
- HTTP: `GET /status` → `200`, empty body.
- Dev dependencies added: `fastapi-cli` (needed by `uv run fastapi dev`) and `httpx2` (Starlette 1.7
  types `TestClient` against it; without it pyright strict sees unknown types and tests warn).
- Test suite: `tests/apps/cms_backend/` with `status.feature` (copied from the reference) run through
  `pytest-bdd`.

### Tests first

- [x] `status.feature` scenario "Check the api status": `GET /status` → 200 and empty body.
- [x] `Settings` defaults: `env == "dev"`, `mongo_url == "mongodb://localhost:27017/daily-trends"`, `port == 5000`.
- [x] `main()` exits with code 1 and logs "Startup failed" when configuration is invalid (subprocess test).
- [x] `main()` exits with code 1 when the port is already in use (subprocess test).
- [x] `Settings` reads `ENV`, `MONGO_URL`, `PORT` from the environment; an invalid `ENV` fails validation.

### Implementation

- [x] Add tool configuration to `pyproject.toml`; delete the `main()` stub in `src/daily_trends_py/__init__.py`.
- [x] Create the package skeleton `apps/cms_backend`, `contexts/cms/feeds`, `contexts/cms/shared` (only modules that contain code).
- [x] Implement `Settings`, `create_app`, the status router and `main()`.
- [x] Update `README.md` (stack line, project layout, run commands: `uv run daily-trends-py`, `uv run fastapi dev`) and `AGENTS.md` (bounded context `cms`, subdomain `feeds`; specs stay in `specs/feeds/`).
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Phase 2: Error format, final handler, middlewares and Swagger

Port `Controller.run`'s per-route error mapping, the final 500 handler, the global middlewares and
Swagger UI.

### Public contracts

- `daily_trends_py.contexts.cms.shared.domain.invalid_argument_error.InvalidArgumentError(Exception)`.
- `daily_trends_py.apps.cms_backend.controllers.ErrorMapping = tuple[type[Exception], int]`.
- `daily_trends_py.apps.cms_backend.controllers.run_controller(action: Callable[[], Awaitable[Response]], exceptions: Sequence[ErrorMapping] = ()) -> Response`:
  first matching `isinstance` wins → `JSONResponse({"error": str(err)}, status)`; unmatched
  `Exception` → `JSONResponse({"error": str(err)}, 500)`. No `Location` header on 302.
- Final handler for `Exception` raised outside `run_controller`: logs it, returns
  `PlainTextResponse(str(exc), 500)`.
- Middlewares: `CORSMiddleware` (open: any origin, the `cors()` default methods, `allow_headers=["*"]`
  so preflights for any requested header succeed as with Express), `GZipMiddleware(minimum_size=1024)`.
  *(`allow_headers` added during implementation: Starlette's default rejected preflights requesting
  non-safelisted headers with 400.)* Known divergence kept: a preflight answers 200 `OK` instead of
  Express's 204.
- `daily_trends_py.apps.cms_backend.routes.register_routes(app: FastAPI) -> None` holds the
  route-order rule; Swagger routes live in `routes/swagger.py`.
- HTTP: `GET /` → Swagger UI HTML loading `/openapi.yml`; `GET /openapi.yml` → `docs/openapi.yml`;
  `/docs`, `/redoc`, `/openapi.json` → 404.
- `docs/openapi.yml` copied from the reference.

### Tests first

- [x] `run_controller` with `InvalidArgumentError("bad")` declared as 400 → 400, `{"error": "bad"}`.
- [x] Test-only `NotFoundError` declared as 404 → 404, body `{"error": "Feed with id <x> not found"}` (literal `<` `>` preserved).
- [x] Test-only `AlreadyExistsError` declared as 302 → 302, `{"error": …}`, no `Location` header.
- [x] Undeclared error (e.g. `InvalidArgumentError` on a route declaring nothing) → 500, `{"error": "<message>"}`.
- [x] First matching mapping wins when several match by inheritance.
- [x] Route raising outside `run_controller` → 500, plain-text body equal to the message, and the error is logged.
- [x] `GET /status` with `Origin` header → `access-control-allow-origin: *`.
- [x] Preflight requesting a custom header succeeds and echoes it in `access-control-allow-headers`.
- [x] Response larger than 1024 bytes with `Accept-Encoding: gzip` → `content-encoding: gzip`.
- [x] `GET /` → 200 HTML referencing `/openapi.yml`; `GET /openapi.yml` → 200 with the file contents; `GET /docs` → 404.

### Implementation

- [x] Add `InvalidArgumentError`, `run_controller`, the final exception handler, middlewares and the Swagger routes; register them in `create_app`.
- [x] Wrap the status route in `run_controller` (declares no errors), as every route will.
- [x] Add a router-registration function with the route-order rule as its docstring.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Phase 3: Mongo client, base repository and event bus

Open one shared Mongo client before accepting traffic, provide the generic persistence operations and
the in-memory event bus that later capabilities use.

### Public contracts

- `daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory.create_mongo_client(url: str) -> AsyncMongoClient[dict[str, object]]`:
  connects (`aconnect`) and returns the client.
- `create_app(settings)` lifespan: creates the client before serving, closes it on shutdown; a
  connection failure aborts startup (→ exit 1 via `main()`).
- `daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_repository.MongoRepository`
  (base class, constructor takes the client and a collection name; database from the URL):
  `_persist(id: str, primitives: Mapping[str, object]) -> None` (`update_one({"_id": id}, {"$set": {...primitives without "id", "_id": id}}, upsert=True)`),
  `_by_id(id: str) -> dict[str, object] | None` (returns the document with `id` set from `_id`),
  `_remove(id: str) -> None`. `_by_criteria` is added in S03.
- `daily_trends_py.contexts.cms.shared.domain.event_bus`: `DomainEvent` (frozen dataclass:
  `event_name: ClassVar[str]`, `aggregate_id: str`, `event_id: str`, `occurred_on: datetime` UTC),
  `DomainEventSubscriber` Protocol, `EventBus` Protocol (`async publish(events: Sequence[DomainEvent]) -> None`,
  `add_subscribers(subscribers: Sequence[DomainEventSubscriber]) -> None`).
- `daily_trends_py.contexts.cms.shared.infrastructure.event_bus.in_memory_event_bus.InMemoryEventBus(EventBus)`:
  `publish` delivers each event to subscribers of its `event_name`; the composition root registers none.
- Test suite: `tests/contexts/cms/shared/...` (integration tests marked `integration`).

### Tests first

- [ ] `integration`: `create_mongo_client` returns a connected client (`ping` succeeds).
- [ ] `integration`: `_persist` upserts by `_id`, does not store `id`, stores `None` as `null`; a second `_persist` with the same id updates with `$set` (fields not sent are kept).
- [ ] `integration`: `_by_id` returns the document with `id` == `_id`; missing id → `None`.
- [ ] `integration`: `_remove` deletes by `_id`; removing a missing id does not raise.
- [ ] `InMemoryEventBus.publish` calls a fake subscriber subscribed to the event's name and skips others.
- [ ] `InMemoryEventBus.publish` with no subscribers completes without error.
- [ ] `status.feature` still passes with the lifespan opening the Mongo client.

### Implementation

- [ ] Implement the client factory, `MongoRepository`, the event-bus port and `InMemoryEventBus`.
- [ ] Wire the client and the event bus in `create_app`'s lifespan (single composition root, strong references kept on `app.state`).
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` (with `docker compose up -d mongo` or a local Mongo) and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest -m integration
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Phase 4: Docker, compose and CI

Ship the app as an image, run it with Mongo via compose, and run the quality gate in CI.

### Public contracts

- `Dockerfile`: `python:3.14-slim` + `uv`, `uv sync --frozen --no-dev`, `CMD ["uv", "run", "--no-sync", "daily-trends-py"]`, `EXPOSE 5000`.
- `.dockerignore`: excludes `.venv`, `reference/`, caches, `.git`.
- `docker-compose.yml`: services `api` (build `.`, `PORT=5000`, `MONGO_URL=mongodb://mongo:27017/daily-trends`, port `5000:5000`, depends on `mongo`) and `mongo` (`mongo` image, `27017:27017`, named volume).
- `.github/workflows/ci.yml`: on push and pull request; `astral-sh/setup-uv`, Python 3.14, `mongo` service, `uv sync --frozen`, then the quality gate from `AGENTS.md`.
- README "Getting started" updated with `docker compose up`.

### Tests first

- [ ] Manual acceptance: `docker compose up --build -d` then `curl -i localhost:5000/status` → `200` with empty body.
- [ ] Manual: stopping Mongo and starting the `api` container exits with code 1 and logs the error.

### Implementation

- [ ] Add `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.github/workflows/ci.yml`.
- [ ] Update `README.md`.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
docker compose up --build -d && curl -i localhost:5000/status && docker compose down
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Next step

Phase 2 is implemented and awaiting review. After review (and an optional `/ai-project-conventional-commit`), run `/ai-project-implement-phase .agents/plans/2026_10_07-s01-foundation/2026_10_07-s01-foundation-plan.md` to implement Phase 3.
