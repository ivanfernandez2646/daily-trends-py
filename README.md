# daily-trends-py

Python port of [daily-trends](https://github.com/ivanfernandez2646/daily-trends): a small news API that stores feeds created through the API and scraped from the front pages of El País and El Mundo.

The port keeps the current behavior of the Node project (same routes, status codes, bodies and data in MongoDB). Known defects are tracked in [`specs/improvements/`](specs/improvements/README.md) and are intentionally not fixed during the migration.

## Stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI, Pydantic v2, pydantic-settings
- MongoDB (PyMongo async)
- httpx and BeautifulSoup for scraping
- ruff, pyright (strict), pytest, pytest-asyncio, pytest-bdd
- Hexagonal architecture with a single bounded context (`feeds`)

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

```bash
uv sync                       # install dependencies
docker compose up -d mongo    # start MongoDB (once the compose file exists)
uv run fastapi dev            # run the API (once the app exists)
```

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
src/<package>/
  apps/<app>/                 entry points and composition root
  contexts/feeds/
    api/                      routers and schemas
    application/              use cases
    domain/                   entities, value objects, ports
    infrastructure/           MongoDB and scraper adapters
    shared/                   shared kernel
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