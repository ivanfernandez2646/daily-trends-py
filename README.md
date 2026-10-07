# daily-trends-py

Python port of [daily-trends](https://github.com/ivanfernandez2646/daily-trends): a small news API that stores feeds created through the API and scraped from the front pages of El País and El Mundo.

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
| `GET /feed/scrap` | Scrape El País and El Mundo and store the results |
| `GET /status` | Health check |

Full contract and error format: [`specs/feeds/S01-foundation.md`](specs/feeds/S01-foundation.md).

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/), Docker (for MongoDB).

Run everything in Docker (API and MongoDB):

```bash
docker compose up --build -d  # API on http://localhost:5000, Swagger UI at /
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
local `.env` (git-ignored): `docker compose` reads it automatically, and `uv run --env-file .env
daily-trends-py` uses it for a local run.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `ENV` | `dev` | `production`, `dev` or `test` |
| `MONGO_URL` | `mongodb://localhost:27017/daily-trends` | MongoDB connection string |
| `PORT` | `5000` | HTTP port |

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
  apps/cms_backend/           entry points and composition root
  contexts/cms/               bounded context
    feeds/                    subdomain
      api/                    routers and schemas
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