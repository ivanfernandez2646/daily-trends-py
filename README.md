# daily-trends-py

A small news site: an API that collects the front-page headlines of Spanish newspapers, a public
reader on top of it, and a CMS for administrators. It is a Python port of
[daily-trends](https://github.com/ivanfernandez2646/daily-trends), built spec-first: the port kept
the original's behavior, and every change since is a spec.

- Web app: <https://daily-trends-web.onrender.com>
- API: <https://daily-trends-api.onrender.com> (Swagger UI at
  [`/docs`](https://daily-trends-api.onrender.com/docs))

## What it does

- Scrapes the front pages of El Mundo, El Español, El Confidencial, La Razón and La Vanguardia at
  startup and every 2 hours, and on demand. El País, scraped by the original, now blocks scrapers
  ([S06](specs/feeds/S06-scrape-external-sources.md)).
- Stores each headline as a feed, with its category and a link to the original article.
- Serves a front page with the newest feeds of each source, and a browse view filtered by category,
  newspaper and Spanish words.
- Lets administrators log in and create, edit and delete feeds, from the API or from the CMS.
- Runs on free plans: Render for the API and the web app, MongoDB Atlas for the data.

Stack: Python 3.14 with [uv](https://docs.astral.sh/uv/), FastAPI, Pydantic v2, MongoDB (PyMongo
async), and httpx with BeautifulSoup for scraping, in a hexagonal architecture. The web app uses
Vite, React and TypeScript.

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/) and Docker (for MongoDB); Node 24 and Corepack for the
web app.

Run the API and MongoDB in Docker:

```bash
docker compose up --build -d      # API on http://localhost:5000, Swagger UI at /docs
docker compose down               # stop (add -v to delete the MongoDB volume)
```

Or run the API locally against MongoDB in Docker:

```bash
uv sync                           # install dependencies
docker compose up -d --wait mongo # start MongoDB
uv run daily-trends-py            # run the API on PORT (default 5000)
uv run fastapi dev                # or with reload, on http://localhost:8000
```

Then the web app, on http://localhost:5173:

```bash
corepack enable                   # once
cd web && pnpm install && pnpm dev
```

To use the CMS, create an administrator and log in at `/login`:

```bash
uv run daily-trends-py create-admin --email admin@example.com
```

On macOS, port 5000 is used by AirPlay Receiver: put `PORT=5123` in a local `.env`.

## Documentation

| Topic | Where |
|---|---|
| Routes, access tokens and errors | [`docs/api.md`](docs/api.md) |
| Settings and administrators | [`docs/configuration.md`](docs/configuration.md) |
| Production: platform, limits, how a merge deploys, runbook | [`docs/deployment.md`](docs/deployment.md) |
| The web app: development, API contract, tests | [`web/README.md`](web/README.md) |
| Behavior, read in order from S00 | [`specs/`](specs/feeds/S00-vision-and-glossary.md) |
| Known defects of the original and their fixes | [`specs/improvements/`](specs/improvements/README.md) |
| Architecture, conventions and the spec-first workflow | [`AGENTS.md`](AGENTS.md) |

## Development

```bash
uv run ruff check .               # lint
uv run ruff format .              # format
uv run pyright                    # type-check
uv run lint-imports               # layer and dependency contracts
uv run pytest                     # tests
uv run pytest -m "not integration"  # tests that do not need MongoDB
```

Tests marked `integration` need MongoDB (`docker compose up -d --wait mongo`). If it does not
answer, the run stops after a 2-second check with a message saying so.

Quality gate, and the web one from `web/`:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run lint-imports \
  && uv run pytest
pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test
```

Git hooks are managed with [pre-commit](https://pre-commit.com/), and commits follow
[Conventional Commits](https://www.conventionalcommits.org/):

```bash
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

Work starts from a spec: agree a plan with `/ai-project-create-plan`, implement it one phase at a
time with `/ai-project-implement-phase`, and commit with `/ai-project-conventional-commit`. See
[`AGENTS.md`](AGENTS.md).
