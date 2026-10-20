# S01 · Foundation

**Status:** draft · **Fidelity:** exact observable behavior; the platform is updated to Python.

## Goal
A running app that starts, reads configuration, connects to Mongo, answers `GET /status` and formats errors the way every later capability expects.

## Behavior
- `GET /status` → 200, empty body.
- Default port `5000` (`PORT`).
- Global middleware: JSON and urlencoded bodies, open CORS, response compression. Swagger UI served from `docs/openapi.yml`.

  > **Superseded by [I06](../improvements/I06-idiomatic-fastapi-layer.md):** only `application/json` bodies are accepted, validated by Pydantic models; a body with another content type (urlencoded included) answers 400 `body: Content type should be application/json`.

  > **Superseded by [I06](../improvements/I06-idiomatic-fastapi-layer.md):** FastAPI generates the OpenAPI document from the code at `GET /openapi.json`, with Swagger UI at `GET /docs` and ReDoc at `GET /redoc`. `docs/openapi.yml` is removed, and `GET /` and `GET /openapi.yml` answer 404.
- Startup: explicit dependency wiring (no DI container). A startup error is logged and the process exits with code 1; uncaught exceptions behave the same.
- Route order rule: fixed routes (`/feed/list`, `/feed/home`, `/feed/scrap`) are registered **before** `/feed/:id`, so a fixed route is never read as an id.

## Error format (used by every capability)
Body `{"error": "<message>"}`, mapped by error type:
| Error | Status | Message |
|---|---|---|
| Invalid argument | 400 | message of the value object (S02) |
| Feed not found | 404 | `Feed with id <{id}> not found` |
| Feed already exists | **302** | `Feed with id <{id}> already exists` |
| Anything else | 500 | `err.message` |

- Messages contain the literal `<` `>` around the id. The 302 has no `Location` header.

> **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** feed already exists answers 409.
- A thrown non-Error value is returned as 500 with the value as JSON.
- A final handler logs unhandled errors and returns 500 with the message.
- Each route maps only the errors it declares (e.g. `GET /feed/home` maps only 400; everything else is 500).

> **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** `GET /feed/home` maps no error to 400, and an invalid stored feed answers 500 on every route.

> **Superseded by [I06](../improvements/I06-idiomatic-fastapi-layer.md):** errors are mapped by kind for every route, with no per-route lists: `InvalidArgumentError` → 400, `NotFoundError` → 404, `ConflictError` → 409, anything else → 500. Every error answers JSON `{"error": "<message>"}`, including the logged 500 of the final handler.

> **Superseded by [I08](../improvements/I08-persistence-and-error-hardening.md):** every 500 answers `{"error": "Internal server error"}` instead of `err.message`; the error, its traceback, the method and the path go only to the log.


## Configuration
- Variables: `ENV` (`production|dev|test`, default `dev`), `MONGO_URL` (default `mongodb://localhost:27017/daily-trends`), `PORT` (default `5000`).
- `dev.json` / `test.json` exist in the original but are **never loaded** (defect, see `improvements/`). The port uses the defaults and environment variables.

> **Superseded by [I04](../improvements/I04-configuration.md):** settings are also read from `.env`, `MONGO_URL` defaults depend on `ENV` (required in production), and the scraping timeout and cooldown are settings.

## Persistence foundation (Mongo)
- One shared client, opened before accepting traffic.
- Collection `feeds`; `_id` = the feed UUID as a string; the `id` field is not stored. Undefined fields are ignored on write.
- Generic operations used by later capabilities: upsert by `_id` (`$set`), find by `_id`, delete by `_id`, search by criteria (defined in S03).

> **Superseded by [I08](../improvements/I08-persistence-and-error-hardening.md):** there is no upsert. Writes are an insert by `_id` (a duplicate `_id` is reported, never overwritten) and an update by `_id` with `$set` that never inserts (a missing document is reported). The `feeds` indexes are created by the first migration.

## Delivery
- Docker image for the app and a `docker-compose` with Mongo for development.
- CI runs the quality gate from `AGENTS.md` (the original workflow uses Node 14/15).
- Event bus: in-memory, `publish` emits each event, no subscribers registered (events defined in S02).

## Acceptance criteria
- `GET /status` → 200 with empty body.
- `docker compose up` starts API + Mongo and `/status` answers 200.
- Error-mapping tests: each error type → status and body above; non-Error value → 500.
- `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest` green.
