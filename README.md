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
for when `--email` is missing, and is stored trimmed and lowercased. Scripts pass the password on
standard input instead, read once from its first line (`--email` is then required):

```bash
printf '%s\n' "$ADMIN_PASSWORD" | uv run daily-trends-py create-admin --email admin@example.com --password-stdin
```
 The command exits with code 1
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

The reader and the CMS live in [`web/`](web/) ([S14](specs/web/S14-web-reader.md),
[S15](specs/web/S15-web-cms.md)): Vite, React and TypeScript, with types generated from the API's
OpenAPI document. Requirements: Node 24 (`web/.nvmrc`) and pnpm through Corepack.

```bash
corepack enable                   # once: provides the pnpm version pinned in web/package.json
cd web && pnpm install
pnpm dev                          # http://localhost:5173
```

Run the API at the same time (see [Getting started](#getting-started)). In development the app
proxies `/feed/…`, `/auth/…` and `/status` to `http://localhost:<PORT>`, with `PORT` from the
repository's `.env` (default `5000`), so the browser talks to a single origin. `VITE_API_BASE_URL`
sets the API origin for a build.

To manage feeds, create an administrator (see [Administrators](#administrators)) and open *Acceder*
in the header, or `/login`. The CMS at `/admin` lists every feed, refreshes the front pages, and
creates, edits and deletes feeds. The session is kept in the tab (`sessionStorage`): it survives a
reload, and ends when the tab is closed, when the token expires (`AUTH_TOKEN_TTL_SECONDS`) or with
*Cerrar sesión*.

After changing a route or a schema in the API, regenerate the contract and commit it:

```bash
pnpm api:generate                 # runs `uv run daily-trends-py openapi` and regenerates the types
```

`uv run daily-trends-py openapi` prints the OpenAPI document without starting the API or reading
any configuration. CI fails when `web/openapi.json` or `web/src/api/schema.gen.ts` are out of date.

End-to-end tests need MongoDB (`docker compose up -d --wait mongo`) and Chromium
(`pnpm exec playwright install chromium`, once). `pnpm e2e` starts the API on port 5199 against the
`daily-trends-e2e` database, with scheduled scraping off, and the built app on port 4173. It also
starts a second API on port 5198 whose tokens expire after 10 seconds, with the app on port 4174,
for the expired session scenario, and creates a test administrator with `create-admin
--password-stdin`.

Web quality gate, from `web/`:

```bash
pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test
```

## Deployment

Production runs on free plans only, with no payment method on any account
([S16](specs/ops/S16-deployment.md)):

| Piece | Where | Plan |
|---|---|---|
| API (`Dockerfile`) | Render web service `daily-trends-api`, region Frankfurt | Free |
| Web app (`web/`) | Render static site `daily-trends-web`, on Render's CDN | Free |
| MongoDB | MongoDB Atlas cluster on AWS `eu-central-1` (Frankfurt) | Free |
| Keep-alive | GitHub Actions scheduled workflow | Free (public repository) |

There are two accounts, Render and Atlas, both created with GitHub and with no card, so neither can
charge. The API and MongoDB share a region, so a query costs milliseconds.

The free plans have limits, and they are accepted:

- The API has 0.1 CPU and 512 MB of memory. It peaks at about 110 MB, and the startup scrape takes
  about 20 s.
- Render gives 750 instance hours a month: enough for **one** free web service always on. A second
  free web service running at the same time would use them up before the month ends.
- Render stops a free web service after 15 minutes without inbound requests and takes about a
  minute to start it again. The keep-alive prevents it.
- The free web service has no persistent disk, no shell and no fixed outbound IP.
- The Atlas free cluster has 512 MB of storage and no backups.

### How a merge deploys

[`render.yaml`](render.yaml) is a Render Blueprint that describes the services. It holds no secret.
CI also runs on every push to `main`, and Render deploys a commit only after its checks pass:

- The API deploys only when the commit changes what goes into its image: `src/`, `pyproject.toml`,
  `uv.lock`, `.python-version`, `Dockerfile` or `.dockerignore`. A merge that only changes `web/`,
  `specs/`, `tests/` or docs does not deploy it.
- The web app deploys only when the commit changes `web/`. A merge that changes both `web/` and
  `src/` deploys both, each after CI passes.
- A deploy that fails its health check (`GET /status`) leaves the previous one serving. That is
  what happens when `MONGO_URL` is missing, or names no database: the API does not start.
- Migrations run when the API starts ([I07](specs/improvements/I07-mongo-migrations.md)). A rollback
  in the Render dashboard does not undo one, so migrations stay additive and the previous version
  still runs.
- The API and the web app deploy separately, even from one pull request, so for a few minutes the
  deployed web app can talk to the previous API, or the other way round. An API contract change is
  therefore additive first: add the new field or route, then use it in the web app, and remove the
  old shape in a later change.

The service's environment is in `render.yaml`: `ENV=production`, `AUTH_SECRET_KEY` generated by
Render when the service is created (regenerating it logs every administrator out), and
`FORWARDED_ALLOW_IPS=*`, so the API trusts the `X-Forwarded-Proto` header of Render's proxy, which
terminates HTTPS. `MONGO_URL` is set in the Render dashboard. Render sets `PORT`, and the other
settings keep their defaults.

The web app is built in `web/` with `corepack enable && pnpm install --frozen-lockfile && pnpm
build`, with Node 24 from `web/.nvmrc` and the `engines` of `web/package.json`, and `dist/` is
published:

- `VITE_API_BASE_URL` in `render.yaml` is the API's public URL. Vite reads it at build time, so
  changing it needs a new build. The browser calls the API with a bearer token and no cookies, and
  CORS already allows any origin, so the API does not need the web app's URL.
- Every path that is not a file is rewritten to `/index.html`, so a reload on `/feeds?…` or a CMS
  route opens the app.
- Files under `/assets/` carry a content hash in their names and are cached for a year.
  `/index.html` is never cached, so a deploy reaches the next page load.

### Keep-alive

[`keep-alive.yml`](.github/workflows/keep-alive.yml) requests `GET <API_URL>/status` every 10
minutes, and on demand from the *Actions* tab. Render's own health checks, which request `/status`
every few seconds, do not count as inbound traffic, so without it the API would stop.

- `API_URL` is a repository variable, not a secret: the URL is public anyway. Until it exists, every
  run is skipped, not failed.
- Each request waits up to 2 minutes and is retried 3 times, so a cold start does not fail the run.
- A failed run marks the workflow red, and GitHub emails the owner. That is the only alerting.
- GitHub delays scheduled runs under load. When one is missed, the API stops after 15 minutes, and
  the next request or run starts it again in about a minute. It scrapes at startup, which repeats
  work but never stores a feed twice.
- GitHub disables scheduled workflows after 60 days without commits. A commit, or enabling the
  workflow again in the *Actions* tab, turns it back on.

### Runbook

These steps are done by hand in the Atlas, Render and GitHub dashboards, in this order, by the
owner.

1. **R1 · Atlas cluster.**
   - Create a free cluster on AWS `eu-central-1`.
   - Create a database user only for the API, with a long random password and read and write
     access to the `daily-trends` database.
   - Allow network access from `0.0.0.0/0`: the free Render service has no fixed IP, so the
     user's password is what protects the cluster.
   - The connection URL names the database, because the API takes it from the URL:
     `mongodb+srv://<user>:<password>@<cluster>/daily-trends?retryWrites=true&w=majority`.
   - The empty cluster needs no preparation: the migrations run when the API starts.
2. **R2 · Scraping from Render.**
   - In the Render dashboard, create a web service by hand: `daily-trends-api-spike`, from this
     repository's `Dockerfile` on `main`, plan free, region Frankfurt.
   - Give it the variables of the API service: the `MONGO_URL` from R1 and any `AUTH_SECRET_KEY`
     of 32 characters or more.
   - Its logs show the migrations, then `Scheduled scraping saved N feeds` and a 200 for each of
     the five sources. A source that fails from Render needs an improvement spec.
3. **R3 · Remove the spike.** Delete `daily-trends-api-spike`, so it neither shares the 750 free
   hours nor takes a name.
4. **R4 · Create the Blueprint.**
   - In Render, create a new Blueprint from this repository on `main`. When it asks for
     `MONGO_URL`, give it the URL from R1.
   - The first deploy passes its health check.
   - Note the API URL (`https://<api>.onrender.com`): the later steps need it.
5. **R5 · First administrator.** The free Render service has no shell, so create the administrator
   from a developer machine against Atlas. The variables go on the command line so that the local
   `.env` does not apply. `create-admin` signs no token, so any key of 32 characters or more works:

   ```bash
   ENV=production MONGO_URL='mongodb+srv://…/daily-trends?…' \
     AUTH_SECRET_KEY=unused-here-but-required-in-production \
     uv run daily-trends-py create-admin --email <email>
   ```

   Use a long password: the login has no rate limit or lockout.
6. **R6 · Check the API.** `GET /status` answers 200, `/docs` loads, `/feed/home` answers feeds, and
   `/auth/login` with the administrator answers a token.
7. **R7 · Keep-alive variable.**
   - In GitHub, *Settings → Secrets and variables → Actions → Variables*, create the repository
     variable `API_URL` with the URL from R4, without a trailing slash.
   - Run the *Keep-alive* workflow by hand from the *Actions* tab: it is green.
   - A day later, every scheduled run is green and the API logs show no restart.
8. **R8 · Check the web app.**
   - Render's Blueprint sync creates `daily-trends-web`, and its first build passes. Its log says
     it uses Node 24; if it shows another version, add `NODE_VERSION` to the web service in
     `render.yaml`.
   - Note the web app's URL. It is `https://daily-trends-web.onrender.com`, unless the name was
     taken and Render added a suffix.
   - The front page shows feeds, and a reload on a deep route, such as
     `/feeds?category=POLITICS`, opens the app on that page.
   - The administrator logs in to the CMS and creates a feed.

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
web/                          the web app: reader (S14), with its own toolchain
  openapi.json                the API contract, generated
  src/api/                    generated types, typed client, query hooks
  src/components/ui/          Tinta design system components
  src/features/feeds/         reader screens and their parts
  src/routes/                 file routes
  tests/e2e/                  Playwright against the real API and MongoDB
specs/
  feeds/                      functional specs of the feeds subdomain, from S00
  users/                      administrators and sessions (S11, S13)
  web/                        the web app (S14, S15) and its design system
  ops/                        deployment (S16)
  improvements/               known defects, out of scope for the port
.agents/                      agent skills and plans
render.yaml                   production on Render (see Deployment)
AGENTS.md                     agent guide (single source of truth)
reference/                    read-only copy of the Node project (git-ignored)
```

## Spec-driven workflow

Work is driven by the specs in `specs/feeds/`, read in order from `S00`:

1. Pick a spec and agree a plan with `/ai-project-create-plan`.
2. Implement one phase at a time with `/ai-project-implement-phase` (TDD, then review).
3. Commit with `/ai-project-conventional-commit`.

See [`AGENTS.md`](AGENTS.md) and [`AGENT-DOCS.md`](AGENT-DOCS.md) for the rules agents follow.