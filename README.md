# daily-trends-py

Python port of [daily-trends](https://github.com/ivanfernandez2646/daily-trends): a small news API that stores feeds created through the API and scraped from the front pages of El Mundo, El Español, El Confidencial, La Razón and La Vanguardia (El País in the original, which now blocks scrapers; see [S06](specs/feeds/S06-scrape-external-sources.md)).

The port keeps the current behavior of the Node project (same routes, status codes, bodies and data in MongoDB). Known defects are tracked in [`specs/improvements/`](specs/improvements/README.md) and are intentionally not fixed during the migration.

## Stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI, Pydantic v2, pydantic-settings
- MongoDB (PyMongo async)
- httpx and BeautifulSoup for scraping
- ruff, pyright (strict), import-linter, pytest, pytest-asyncio, pytest-bdd
- Hexagonal architecture with a single bounded context (`cms`, subdomains `feeds` and `users`)

## API

| Method and path | Description | Token |
|---|---|---|
| `PUT /feed/{id}` | Create a feed (source `CMS`) | yes |
| `GET /feed/{id}` | Get a feed | |
| `PATCH /feed/{id}` | Update title and/or description | yes |
| `DELETE /feed/{id}` | Delete a feed | yes |
| `GET /feed/list` | Browse feeds newest first, a page at a time (`limit`, `cursor`); filter by `category`, `source` and Spanish words in `q` | |
| `GET /feed/home` | Up to 10 stored scraped feeds: the 2 newest of each source, filled with the newest of any | |
| `GET /feed/scrap` | Scrape every source now and store the results; waits for a scraping run in progress | yes |
| `POST /auth/login` | Exchange an administrator's email and password for a bearer access token | |
| `GET /auth/me` | The administrator behind the token and when the token expires | yes |
| `GET /status` | Health check | |

Routes marked *Token* need `Authorization: Bearer <token>` from `POST /auth/login` (see
[Administrators](#administrators)). Without a token they answer 401
`{"error": "Authentication required"}`, and with an invalid or expired one 401
`{"error": "Invalid or expired access token"}`, before the body or the id is checked.
`GET /auth/me` also answers 401 `{"error": "Invalid or expired access token"}` when the token's
user no longer exists ([S13](specs/users/S13-admin-session.md)).

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
| `UnauthorizedError` (`InvalidCredentials`, `MissingAccessToken`, `InvalidAccessToken`), with `WWW-Authenticate: Bearer` | 401 |
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
| `SCRAPE_TIMEOUT_SECONDS` | `10` | Timeout of each request to a scraped site, > 0 |
| `SCRAPE_SCHEDULE_ENABLED` | `true` | Scrape every source at startup and then every `SCRAPE_INTERVAL_SECONDS`; `false` leaves only `/feed/scrap` |
| `SCRAPE_INTERVAL_SECONDS` | `7200` | Time from the end of a scheduled run to the start of the next one, > 0 |
| `AUTH_SECRET_KEY` | `dev` and `test`: a fixed development key, `production`: required | Signs the access tokens (HS256), at least 32 characters, never shown in errors or logs. Changing it invalidates every token. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `AUTH_TOKEN_TTL_SECONDS` | `28800` (8 hours) | How long an access token stays valid after login, > 0 |

### Administrators

Administrators manage the CMS. There is no registration endpoint: create one from the command line,
against the database of `MONGO_URL` (pending migrations are applied first, so an empty database
works):

```bash
uv run daily-trends-py create-admin --email admin@example.com
```

The password is asked twice without echo and needs at least 12 characters. The email is asked
for when `--email` is missing, and is stored trimmed and lowercased. The command exits with code 1
and creates nothing for an invalid email, a short password, passwords that do not match or an
email that already exists. Changing passwords and removing users are done directly in MongoDB
([S11](specs/users/S11-authentication.md)).

Log in to get an access token:

```bash
curl -s localhost:5000/auth/login -H 'Content-Type: application/json' \
  -d '{"email": "admin@example.com", "password": "<password>"}'
# {"access_token": "<jwt>", "token_type": "bearer", "expires_in": 28800}
```

Send it as `Authorization: Bearer <jwt>`. `GET /auth/me` answers who the token belongs to and
when it expires:

```bash
curl -s localhost:5000/auth/me -H 'Authorization: Bearer <jwt>'
# {"id": "<uuid>", "email": "admin@example.com", "created_at": "…Z", "token_expires_at": "…Z"}
```

In Swagger UI (`/docs`), paste it in *Authorize*. An
unknown email and a wrong password both answer 401 `{"error": "Invalid email or password"}`.

## Web app

The reader lives in [`web/`](web/) ([S14](specs/web/S14-web-reader.md)): Vite, React and TypeScript,
with types generated from the API's OpenAPI document. Requirements: Node 24 (`web/.nvmrc`) and
pnpm through Corepack.

```bash
corepack enable                   # once: provides the pnpm version pinned in web/package.json
cd web && pnpm install
pnpm dev                          # http://localhost:5173
```

Run the API at the same time (see [Getting started](#getting-started)). In development the app
proxies `/feed/…`, `/auth/…` and `/status` to `http://localhost:<PORT>`, with `PORT` from the
repository's `.env` (default `5000`), so the browser talks to a single origin. `VITE_API_BASE_URL`
sets the API origin for a build.

After changing a route or a schema in the API, regenerate the contract and commit it:

```bash
pnpm api:generate                 # runs `uv run daily-trends-py openapi` and regenerates the types
```

`uv run daily-trends-py openapi` prints the OpenAPI document without starting the API or reading
any configuration. CI fails when `web/openapi.json` or `web/src/api/schema.gen.ts` are out of date.

Web quality gate, from `web/`:

```bash
pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build
```

## Development

```bash
uv run ruff check .           # lint
uv run ruff format .          # format
uv run pyright                # type-check
uv run lint-imports           # layer and dependency contracts
uv run pytest                 # tests
uv run pytest -m "not integration"  # tests that do not need MongoDB
```

Tests marked `integration` need MongoDB (`docker compose up -d --wait mongo`). If it does not
answer, the run stops after a 2-second check with a message saying so.

Quality gate:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run lint-imports \
  && uv run pytest
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
    users/                    subdomain: administrators
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