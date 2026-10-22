# API

The full contract is in [`specs/feeds/`](../specs/feeds/) from S01, with the changes of
[I06](../specs/improvements/I06-idiomatic-fastapi-layer.md), and in
[`specs/users/`](../specs/users/) for administrators. FastAPI generates the OpenAPI document from the
code: Swagger UI at `/docs`, ReDoc at `/redoc` and the document at `/openapi.json`.

## Routes

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

Feed JSON uses snake_case keys (`created_at`, `updated_at`), with dates in UTC with `Z` and a
fractional part only when it is not zero (`2026-10-12T08:00:00Z`, `2026-10-12T08:00:00.123000Z`).

## Access tokens

Routes marked *Token* need `Authorization: Bearer <token>` from `POST /auth/login`. Administrators
are created from the command line (see [Administrators](configuration.md#administrators)).

```bash
curl -s localhost:5000/auth/login -H 'Content-Type: application/json' \
  -d '{"email": "admin@example.com", "password": "<password>"}'
# {"access_token": "<jwt>", "token_type": "bearer", "expires_in": 28800}

curl -s localhost:5000/auth/me -H 'Authorization: Bearer <jwt>'
# {"id": "<uuid>", "email": "admin@example.com", "created_at": "…Z", "token_expires_at": "…Z"}
```

In Swagger UI, paste the token in *Authorize*.

- An unknown email and a wrong password both answer 401 `{"error": "Invalid email or password"}`.
- Without a token, a protected route answers 401 `{"error": "Authentication required"}`, and with an
  invalid or expired one 401 `{"error": "Invalid or expired access token"}`, before the body or the
  id is checked.
- `GET /auth/me` also answers 401 `{"error": "Invalid or expired access token"}` when the token's
  user no longer exists ([S13](../specs/users/S13-admin-session.md)).

## Errors

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
