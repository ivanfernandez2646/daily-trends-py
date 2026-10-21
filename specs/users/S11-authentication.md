# S11 · Authentication

**Status:** draft · **Fidelity:** new capability, breaks the write contract on purpose (every write
needs a token). Depends on S01, S02, S04, S05, S06, I04, I06 and I07. Resolves the authentication
half of improvement #15 from `improvements/README.md`. Independent of S09 and S10.

## Goal
Only administrators manage the CMS: creating, updating and deleting feeds and running a scrape need
a signed access token, obtained by logging in with an email and a password. Reading feeds stays
public. The solution is self-hosted and free: users live in Mongo, passwords are hashed with Argon2
and tokens are signed JWTs. There is no external identity provider.

## Bounded context
A new subdomain, `cms/users`, next to `cms/feeds`, with its own domain, application and
infrastructure layers, its dishka provider and its router (`AGENTS.md`). `cms/feeds` does not
depend on `cms/users`: routes are protected in the HTTP layer of `apps/cms_backend`.

## Domain

### `User`
Aggregate root. Every user is an administrator: there are no roles or permissions.

| Field | Type | Rule |
|---|---|---|
| `id` | `UserId` | UUID, like `FeedId` (S02). |
| `email` | `UserEmail` | See below. Unique among users. |
| `password_hash` | `UserPasswordHash` | Required string. Never the plain password, never returned, never logged. |
| `created_at` | `UserCreatedAt` | Timezone-aware UTC instant from the `Clock` (I09). |

- `User.create` emits no domain event.

### `UserEmail`
- Trimmed and lowercased before validation and storage, so `  Admin@Example.com ` and
  `admin@example.com` are the same user.
- Valid when it has exactly one `@`, a non-empty local part, and a domain with at least one `.`
  and no blank labels. No DNS or deliverability check.
- Otherwise an invalid argument: `<UserEmail> does not allow the value <{value}>`, with the value
  as received.

### Plain password
- Not stored and not a field of `User`; it only crosses the use cases that hash or verify it.
- To create a user it must have at least 12 characters, otherwise an invalid argument:
  `<UserPassword> must have at least 12 characters`. The message never shows the value.
- To log in, any string is accepted: a short password just fails as wrong credentials.

### Errors
| Error | Kind | Message |
|---|---|---|
| `UserAlreadyExists` | `ConflictError` (409) | `User with email <{email}> already exists` |
| `InvalidCredentials` | `UnauthorizedError` (401) | `Invalid email or password` |
| `InvalidAccessToken` | `UnauthorizedError` (401) | `Invalid or expired access token` |
| `MissingAccessToken` | `UnauthorizedError` (401) | `Authentication required` |

- `UnauthorizedError` is a new error kind in `cms/shared/domain`, mapped to 401 by
  `apps/cms_backend/errors.py` like the other kinds (I06). Every 401 carries the header
  `WWW-Authenticate: Bearer`.

## Ports
The plan names them; the behavior they guarantee is:
- **User repository:** save a new user (a duplicate email reports `UserAlreadyExists`, I08 style:
  insert only) and find a user by email.
- **Password hasher:** hash a plain password and verify a plain password against a hash. The Argon2
  adapter uses `pwdlib` with its recommended parameters. Tests use a fake hasher.
- **Access token issuer and verifier:** issue a token for a user id and verify a token, returning
  the user id. The JWT adapter uses `PyJWT`.

## Access tokens
- JWT signed with HS256 and the `AUTH_SECRET_KEY` setting. Claims: `sub` (the user id), `iat` and
  `exp`. Any other algorithm, `none` included, is rejected.
- Valid for `AUTH_TOKEN_TTL_SECONDS` from the moment it is issued. `iat` and `exp` come from the
  `Clock`, and expiry is checked against the `Clock` with no leeway, so tests can fix the time.
- Verification checks only the signature, the algorithm and `exp`. It does not read the database:
  a token stays valid until it expires. There is no revocation, refresh token or logout; changing
  `AUTH_SECRET_KEY` invalidates every token at once.

## HTTP

### `POST /auth/login`
- Body: `{"email": "<string>", "password": "<string>"}`, both required strings. A missing field, a
  value that is not a string or a body that is not JSON → 400 with the usual format (S01, I06).
- An email that `UserEmail` rejects is not a 400: it is treated as an unknown email.
- Valid credentials → 200:
  ```json
  {"access_token": "<jwt>", "token_type": "bearer", "expires_in": 28800}
  ```
  `expires_in` is `AUTH_TOKEN_TTL_SECONDS`.
- Unknown email or wrong password → 401 `{"error": "Invalid email or password"}`. The answer is the
  same in both cases, and an unknown email still runs one password verification against a fixed
  dummy hash, so response time does not reveal which emails exist.
- The route is public and documented in the `auth` OpenAPI tag.

### Protected routes
| Route | Protected |
|---|---|
| `PUT /feed/{id}` | yes |
| `PATCH /feed/{id}` | yes |
| `DELETE /feed/{id}` | yes |
| `GET /feed/scrap` | yes: it writes feeds (S06) |
| `GET /feed/list`, `GET /feed/{id}`, `GET /feed/home` | no |
| `GET /status`, `GET /docs`, `GET /redoc`, `GET /openapi.json` | no |

- A protected route needs the header `Authorization: Bearer <token>`. The scheme is
  case-insensitive (`bearer` is accepted).
- No `Authorization` header, an empty one, or another scheme (`Basic ...`) → 401
  `{"error": "Authentication required"}`.
- A token that is malformed, has a bad signature, another algorithm, no `sub`, or has expired → 401
  `{"error": "Invalid or expired access token"}`.
- Authentication runs **before** the request is validated or the use case runs: an unauthenticated
  request answers 401 even when its body is invalid (would be 400) or its feed does not exist
  (would be 404). An unauthenticated `/feed/scrap` never starts a scrape.
- The protected routes are otherwise unchanged: same bodies, statuses and errors as today once the
  token is valid. The feed `author` is still sent by the client, not taken from the user.
- OpenAPI declares an HTTP bearer security scheme on the protected routes and a 401 response on
  each, so Swagger UI shows the *Authorize* button: the user calls `/auth/login`, copies
  `access_token` and pastes it there. Swagger's OAuth2 password form is not used, because it sends
  an urlencoded body and the API only accepts JSON (I06).
- CORS is unchanged: it already allows the `Authorization` header.

## Creating administrators
There is no registration endpoint. Administrators are created from the command line:

```bash
uv run daily-trends-py create-admin [--email <email>]
```

- `daily-trends-py` with no arguments still runs the API (S01). `create-admin` is a subcommand of
  the same entry point.
- It asks for the email when `--email` is not given, then for the password twice without echoing it
  (`getpass`). The two passwords must match.
- It reads the same settings as the API (I04), connects to `MONGO_URL` and applies pending
  migrations before writing, so it works on an empty database.
- On success it prints `Admin <{email}> created` and exits with code 0.
- An invalid email, a short password, passwords that do not match, or an existing email → prints
  the error message to stderr and exits with code 1, without creating anything. The password is
  never printed.
- Changing or resetting a password, listing users and deleting users are out of scope. Until a
  later spec adds them, they are done directly in Mongo.

## Persistence
- Collection `users`; `_id` is the user UUID as a string, like feeds (S01). Fields: `email`,
  `password_hash`, `created_at` (BSON date, I05).
- A new migration, `m0002_users_indexes`, creates a unique index on `email` (I07). The index is
  what guarantees uniqueness; a duplicate-key error on insert is reported as `UserAlreadyExists`.
- Reading a stored user that is not valid answers 500, like an invalid stored feed (I01, I09).

## Configuration (I04)
| Variable | Default | Rule |
|---|---|---|
| `AUTH_SECRET_KEY` | `dev` and `test`: a fixed development value; `production`: **none** | Required in production, at least 32 characters. Never echoed in errors or logs. |
| `AUTH_TOKEN_TTL_SECONDS` | `28800` (8 hours) | Greater than 0. |

- An invalid value stops startup with exit code 1, like any invalid setting. The error names the
  variable and never shows the secret.
- `.env.example` and the project `README.md` list both variables, with a command to generate a key
  (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).
- New dependencies: `pyjwt` and `pwdlib[argon2]`. Both are free and open source.

## Out of scope
Registration, password reset and change, email verification, roles and permissions, refresh tokens,
revocation and logout, login rate limiting or lockout, OAuth or SSO providers, sessions or cookies,
and setting the feed author from the logged-in user.

## Edge cases
- `create-admin` with `Admin@Example.com`, then login with `admin@example.com` → 200.
- Login with the right email and a wrong password, and login with an unknown email → the same 401
  body.
- Login with `email: "not-an-email"` → 401, not 400.
- Login body `{"email": "a@b.co"}` → 400 for the missing `password`.
- Token issued at `10:00:00` with a TTL of 3600 → valid at `10:59:59`, 401 at `11:00:00`.
- A token signed with another key, or a valid token with one character changed → 401
  `Invalid or expired access token`.
- `Authorization: Basic YWRtaW46c2VjcmV0` on `DELETE /feed/{id}` → 401 `Authentication required`.
- `PUT /feed/{id}` without a token and with an invalid body → 401, not 400.
- `DELETE /feed/{id}` without a token on a missing feed → 401, not 404.
- `GET /feed/scrap` without a token → 401 and no scraper runs.
- `GET /feed/list` without a token → 200, unchanged.
- `ENV=production` without `AUTH_SECRET_KEY`, or with a 20-character key → startup fails with exit
  code 1 and a message naming `AUTH_SECRET_KEY`.
- Running `create-admin` twice with the same email → the second run exits with code 1 and
  `User with email <admin@example.com> already exists`.

## Acceptance criteria
- Domain tests: `UserEmail` normalization and every invalid form; the password length rule and that
  its message hides the value; `User.create`.
- Use-case tests with fakes for the repository, hasher, token issuer and clock: login succeeds,
  fails the same way for an unknown email and a wrong password, and verifies against the dummy hash
  when the email is unknown; creating an admin hashes the password, saves the user and reports a
  duplicate email.
- Adapter tests: the Argon2 hasher verifies its own hashes and rejects a wrong password; the JWT
  adapter round-trips a user id and rejects an expired token, a bad signature, `alg: none`, another
  algorithm and a token without `sub`.
- Repository integration tests against real Mongo: save and find by email, duplicate email, the
  unique index from `m0002_users_indexes`, and an invalid stored user.
- HTTP tests: `/auth/login` for 200, 400 and 401; for each protected route, 401 without a token, with
  another scheme, with an invalid and with an expired token, and the current behavior with a valid
  token; 401 wins over 400 and 404; `/feed/scrap` without a token runs no scraper; public routes
  answer without a token; 401 responses carry `WWW-Authenticate: Bearer`.
- Existing feed HTTP tests send a valid token to the protected routes through a shared test fixture.
- OpenAPI test: the bearer security scheme is declared on exactly the protected routes, and
  `/auth/login` is documented.
- CLI tests: `create-admin` creates a user, rejects mismatched passwords, short passwords, invalid
  emails and duplicates with exit code 1, and never prints the password.
- Settings tests: the defaults, the production requirement, the minimum key length and the TTL rule.
- `S00-vision-and-glossary.md` lists S11 and no longer has authentication out of scope.
  `improvements/README.md` links S11 for the authentication half of #15. The project `README.md`
  explains how to create an admin and log in.
- The quality gate from `AGENTS.md` passes.
