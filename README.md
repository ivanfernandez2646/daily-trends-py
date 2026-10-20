# daily-trends-py

Python port of [daily-trends](https://github.com/ivanfernandez2646/daily-trends): a small news API that stores feeds created through the API and scraped from the front pages of El Mundo and El Español (El País in the original, which now blocks scrapers; see [S06](specs/feeds/S06-scrape-external-sources.md)).

The port keeps the current behavior of the Node project (same routes, status codes, bodies and data in MongoDB). Known defects are tracked in [`specs/improvements/`](specs/improvements/README.md) and are intentionally not fixed during the migration.

## Stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI, Pydantic v2, pydantic-settings
- MongoDB (PyMongo async)
- httpx and BeautifulSoup for scraping
- ruff, pyright (strict), pytest, pytest-asyncio, pytest-bdd
- Hexagonal architecture with a single bounded context (`cms`, subdomain `feeds`)

## API

| Method and path | Description |
|---|---|
| `PUT /feed/{id}` | Create a feed (source `CMS`) |
| `GET /feed/{id}` | Get a feed |
| `PATCH /feed/{id}` | Update title and/or description |
| `DELETE /feed/{id}` | Delete a feed |
| `GET /feed/list` | List all feeds, newest first |
| `GET /feed/home` | 10 newest scraped feeds; scrapes on demand if the newest is older than today |
| `GET /feed/scrap` | Scrape El Mundo and El Español and store the results |
| `GET /status` | Health check |

FastAPI generates the OpenAPI document from the code: Swagger UI at `/docs`, ReDoc at `/redoc` and
the document at `/openapi.json`. Feed JSON uses snake_case keys (`created_at`, `updated_at`), with
dates in UTC with `Z` and a fractional part only when it is not zero
(`2026-10-12T08:00:00Z`, `2026-10-12T08:00:00.123000Z`).

### Errors

Every error answers JSON `{"error": "<message>"}`. The status depends on the kind of error, for
every route:

| Error | Status |
|---|---|
| Request that fails schema validation | 400 |
| `InvalidArgumentError` (a blank title, an id that is not a UUID) | 400 |
| `NotFoundError` (`FeedNotFound`) | 404 |
| `ConflictError` (`FeedAlreadyExists`) | 409 |
| Framework errors: unknown route, method not allowed, unreadable body | their status (404, 405, 400) |
| Anything else | 500 `{"error": "Internal server error"}`, with the CORS headers, logged once with the method and path |

A validation message lists each problem as `<field>: <reason>`, joined with `; `, for example
`title: Field required; author: Field required`. Bodies must be `application/json`: any other
content type answers `body: Content type should be application/json`, and malformed JSON or an
array is also reported at `body`. A missing body reads as `{}`. Domain messages keep the value
between angle brackets: `<FeedTitle> is mandatory. Current value: <  >`.

Full contract: [`specs/feeds/`](specs/feeds/) from S01, with the changes of
[I06](specs/improvements/I06-idiomatic-fastapi-layer.md).

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/), Docker (for MongoDB).

Run everything in Docker (API and MongoDB):

```bash
docker compose up --build -d  # API on http://localhost:5000, Swagger UI at /docs
docker compose down           # stop (add -v to delete the MongoDB volume)
```

Or run the API locally against MongoDB in Docker:

```bash
uv sync                           # install dependencies
docker compose up -d --wait mongo # start MongoDB
uv run fastapi dev                # run the API with reload on http://localhost:8000
uv run daily-trends-py            # run the API on PORT (default 5000)
```

On macOS, port 5000 is used by AirPlay Receiver. Either turn the receiver off or put `PORT=5123` in a
local `.env` (git-ignored): both the API and `docker compose` read it.

### Configuration

Settings are read from environment variables, then from a `.env` file in the working directory
(see `.env.example`), then from the defaults below. The test suite never reads `.env`. Invalid
settings stop the API at startup with exit code 1.

| Variable | Default | Description |
|---|---|---|
| `ENV` | `dev` | `production`, `dev` or `test`; selects the default `MONGO_URL` |
| `MONGO_URL` | `dev`: `mongodb://localhost:27017/daily-trends-dev`, `test`: `mongodb://localhost:27017/daily-trends-test`, `production`: required | MongoDB connection string |
| `PORT` | `5000` | HTTP port |
| `TIMEZONE` | `Europe/Madrid` | IANA zone that decides when a business day starts; the server's `TZ` is ignored |
| `SCRAP_TIMEOUT_SECONDS` | `10` | Timeout of each request to a scraped site, > 0 |
| `SCRAP_COOLDOWN_SECONDS` | `300` | Minimum time between background front page refreshes, ≥ 0 (0 disables it) |

## Development

```bash
uv run ruff check .           # lint
uv run ruff format .          # format
uv run pyright                # type-check
uv run pytest                 # tests
```

Quality gate:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

Git hooks are managed with [pre-commit](https://pre-commit.com/):

```bash
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Project layout

```text
src/daily_trends_py/
  apps/cms_backend/           entry points, DI container and providers, routers, schemas, errors
  contexts/cms/               bounded context
    feeds/                    subdomain
      application/            use cases
      domain/                 entities, value objects, ports
      infrastructure/         MongoDB and scraper adapters
    shared/                   shared kernel of the context
tests/                        mirrors src/ (apps/cms_backend, contexts/cms/...)
specs/
  feeds/                      functional specs (S00 to S07)
  improvements/               known defects, out of scope for the port
.agents/                      agent skills and plans
AGENTS.md                     agent guide (single source of truth)
reference/                    read-only copy of the Node project (git-ignored)
```

## Spec-driven workflow

Work is driven by the specs in `specs/feeds/`, read in order from `S00`:

1. Pick a spec and agree a plan with `/ai-project-create-plan`.
2. Implement one phase at a time with `/ai-project-implement-phase` (TDD, then review).
3. Commit with `/ai-project-conventional-commit`.

See [`AGENTS.md`](AGENTS.md) and [`AGENT-DOCS.md`](AGENT-DOCS.md) for the rules agents follow.