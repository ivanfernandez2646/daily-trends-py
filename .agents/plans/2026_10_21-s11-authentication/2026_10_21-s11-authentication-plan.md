---
name: 's11-authentication'
description: 'Administrators live in Mongo with Argon2 hashes, log in at POST /auth/login for an HS256 JWT, and every feed write and /feed/scrap needs that bearer token'
spec: 'specs/users/S11-authentication.md'
branch: 'feat/s11-authentication'
created_at: '2026-10-21T09:19:25Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-21T10:30:00Z'
---

# S11 · Authentication

## Goal

Add the `cms/users` subdomain. Administrators are created with `uv run daily-trends-py create-admin`
and log in with `POST /auth/login`, which returns a signed access token. `PUT`, `PATCH` and
`DELETE /feed/{id}` and `GET /feed/scrap` answer 401 without a valid
`Authorization: Bearer <token>`, and authentication runs before any other check. Reading feeds
stays public.

## Context

- **Error kinds:** `apps/cms_backend/errors.py` maps error kinds through `_STATUS_BY_KIND`, and
  `_answer_with(status)` builds each handler. `UnauthorizedError` is a new kind mapped to 401, and
  its handler adds `WWW-Authenticate: Bearer`, so `_answer_with` needs per-kind headers.
- **401 before 400 (agreed: option B):** FastAPI reads and parses the JSON body before it resolves
  any `Depends`, and `JsonBodyRoute` rejects a wrong content type even earlier. With a plain
  dependency, a malformed body would answer 400 before the 401. The fix has three parts:
  - **`AdminRoute(JsonBodyRoute)`:** its handler wrapper authenticates first and then delegates to
    `JsonBodyRoute`'s rules.
  - **`admin_router`:** the protected routes move to it, with `route_class=AdminRoute`. FastAPI's
    route decorators do not accept `route_class_override`, so the class is set per router.
  - **OpenAPI:** the router declares `dependencies=[Security(BEARER)]`, so the document shows the
    bearer scheme and the *Authorize* button. `BEARER` is an `HTTPBearer(auto_error=False)`, and
    `AdminRoute` reuses its header parsing: `await BEARER(request)` returns `None` when the header
    is missing, empty or uses another scheme, and the scheme check ignores case.
- **Route order:** `register_routes` includes `feed.admin_router` before `feed.router`, so
  `GET /feed/scrap` is matched before `GET /feed/{id}`. Starlette serves the first route whose path
  and method both match, so `PUT /feed/{id}` in the admin router never hides `GET /feed/{id}`.
- **Resolving inside a route:** `AdminRoute` gets the verifier from the request's dishka container,
  `request.state.dishka_container`, which `setup_dishka` sets up. `tests/test_architecture.py` only
  forbids `app.state`.
- **Argon2 is CPU-bound:** `PasswordHasher` is async, and the `pwdlib` adapter runs it in
  `asyncio.to_thread` so it never blocks the event loop.
- **Dummy hash:** `verify(password, None)` checks the password against a dummy hash the adapter
  computes once (lazily, then cached) and returns `False`. Login with an unknown email costs the
  same as a wrong password. There is no Argon2 cost each time the app starts in tests, and the fake
  hasher can record the `None` call.
- **PyJWT checks time with the system clock:** `jwt.decode` runs with
  `algorithms=["HS256"]`, `options={"verify_exp": False, "verify_iat": False, "verify_nbf": False,
  "require": ["sub", "exp"]}`. The adapter then rejects the token when `clock.now() >= exp`, so a
  token issued at 10:00:00 with a TTL of 3600 is valid at 10:59:59 and rejected at 11:00:00. A `sub`
  that `UserId` rejects is also `InvalidAccessToken`, never a 400. Verification never reads Mongo.
- **Duplicate email:** `MongoRepository._insert` reports `False` only for a duplicate `_id` and
  raises any other duplicate key. It gains `unique_key: str = "_id"`, and `MongoUserRepository`
  passes `"email"`.
- **Mongo field names:** users store `created_at` in snake_case, as the spec says, even though feeds
  keep `createdAt`.
- **Migrations:** `m0003_users_indexes` is appended to `MIGRATIONS` and creates the named unique
  index `email_unique` on `users.email`. It uses plain strings and no domain imports
  (`ai-project-mongo-migrations` skill).
- **Settings:** `Settings` already uses `hide_input_in_errors=True` and a `mode="before"` validator
  for env-dependent defaults (`MONGO_URL`). `AUTH_SECRET_KEY` follows the same pattern.
  - **Agreed:** the 32-character minimum applies in every ENV.
  - The dev/test default is a fixed value at least 32 characters long.
  - The field is a `SecretStr`.
- **CLI:** `main()` today takes `migrations` as a positional argument, and `test_main` calls
  `main([Migration(...)])`. The new signature is `main(argv=None, *, migrations=MIGRATIONS)`, so
  those calls change to the keyword form. `create-admin` builds the same container, so it applies
  pending migrations before resolving `UserCreator`. Its prompts are injectable callables
  (`input`, `getpass.getpass`) so tests pass fakes and need no patching. **Agreed:** passwords that
  differ print `Passwords do not match`.
- **Test harness:**
  - **Protected-route calls:** about 50 calls in `tests/apps/cms_backend`, plus the BDD steps,
    hit protected routes.
  - **Default token:** the `client` fixture carries a valid admin token by default. The token is
    issued by the app's `AccessTokenIssuer` for a random `UserId`; no user is stored, because
    verification does not read Mongo. This keeps the existing tests unchanged.
  - **Anonymous client:** `anonymous_client` removes the header from the same client for the 401
    tests.
  - **Cleanup:** the fixture also clears `users`.
- **Import contract:** a new import-linter contract stops `daily_trends_py.contexts.cms.feeds` from
  importing `daily_trends_py.contexts.cms.users`. The existing wildcard contracts already cover the
  new layers.
- **Docs:** `S00` and `improvements/README.md` already reference S11 on `main`. Only `README.md`
  and `.env.example` change.
- **Dependencies:** `uv add pyjwt "pwdlib[argon2]"`.

## Phases

## Phase 1: Create administrators

The `cms/users` subdomain up to persistence. With this phase, `uv run daily-trends-py create-admin`
stores an administrator with an Argon2 hash in a database it migrates first. No HTTP change.

### Public contracts

- `contexts/cms/users/domain`:
  - **Identity and data:**
    - `UserId(UuidValueObject)`.
    - `UserEmail(StringValueObject)`, frozen. It is trimmed and lowercased, then validated: exactly
      one `@`, a non-empty local part, and a domain with a `.` and no blank labels. Otherwise it
      raises `InvalidArgumentError("<UserEmail> does not allow the value <{value as received}>")`.
    - `UserPasswordHash(RequiredStringValueObject)`, frozen, with `repr=False` on its value.
    - `UserCreatedAt(RequiredDateTimeValueObject)`.
  - **`UserPassword`:** a frozen dataclass, `value: str` with `repr=False`. Fewer than 12 characters
    raises `InvalidArgumentError("<UserPassword> must have at least 12 characters")`. It is not a
    field of `User`.
  - **`User`:**
    - `User(AggregateRoot)` with `@dataclass(eq=False)` and the fields `id, email, password_hash,
      created_at`.
    - `User.create(*, id, email, password_hash, now) -> User` records no event.
    - `to_primitives()` and `from_primitives()`, with a `UserPrimitives` `TypedDict`.
  - **Errors:** `UserAlreadyExists(ConflictError)`, which takes a `UserEmail` and says
    `User with email <{email}> already exists`.
  - `UserRepository(Protocol)`:
    - `async create(user: User) -> None` raises `UserAlreadyExists` and inserts nothing when the
      email is taken.
    - `async find_by_email(email: UserEmail) -> User | None`.
  - `PasswordHasher(Protocol)`:
    - `async hash(password: UserPassword) -> UserPasswordHash`.
    - `async verify(password: str, hash: UserPasswordHash | None) -> bool`. With `None`, it verifies
      against a dummy hash and returns `False`.
- `contexts/cms/users/application/create/user_creator.py`:
  - `UserCreator(repository, hasher, clock)`.
  - `async execute(*, email: str, password: str) -> User` validates the email and the password
    before hashing.
- `contexts/cms/users/infrastructure`:
  - **Hashing:** `Argon2PasswordHasher()` uses `PasswordHash.recommended()` from `pwdlib` and runs
    in `asyncio.to_thread`.
  - **Persistence:**
    - `MongoUserRepository(client)` uses the collection `users`.
    - Documents are `{_id, email, password_hash, created_at}`.
    - `InvalidStoredUser(Exception)`: a stored user the domain rejects, answered as a 500.
- `contexts/cms/shared/infrastructure/persistence/mongo/mongo_repository.py`:
  `_insert(document, unique_key: str = "_id") -> bool`.
- Migration `m0003_users_indexes`: `IndexModel([("email", ASCENDING)], name="email_unique",
  unique=True)` on `users`.
- `apps/cms_backend`:
  - **Wiring:** `providers/users.py` holds `UsersProvider` and `USER_USE_CASES = (UserCreator,)`.
    The container adds the provider, and `STARTUP_DEPENDENCIES` adds the use cases.
  - **`main.py`:** `main(argv: Sequence[str] | None = None, *, migrations=MIGRATIONS) -> None`.
    With no subcommand, it runs the API as today. `create-admin [--email EMAIL]`:
    - Prompts for the email when `--email` is missing, then for the password twice with `getpass`.
    - On success it prints `Admin <{email}> created` to stdout and exits 0.
    - An invalid email, a short password, `Passwords do not match` or an existing email prints the
      message to stderr and exits 1, and creates nothing.
    - It never prints the password.
  - **CLI module:** `cli.py` holds `create_admin(settings, *, email, prompt, secret_prompt,
    migrations) -> int`, the testable core that returns the exit code.
- `pyproject.toml`:
  - Dependencies `pyjwt` and `pwdlib[argon2]`.
  - An import-linter contract: feeds does not import users.
- Tests:
  - **Mothers:** `UserMother`, `UserEmailMother`, `UserIdMother` and `UserPasswordMother`.
  - **Fakes:** `InMemoryUserRepository` and `FakePasswordHasher`. The fake hash is
    `hashed:<password>`, and the fake records each `verify` call.
  - `UserDocumentMother`.

### Tests first

- [x] `tests/contexts/cms/users/domain/test_user_value_objects.py`:
  - `UserEmail` turns `  Admin@Example.com ` into `admin@example.com`.
  - It rejects no `@`, two `@`, an empty local part, a domain without a `.`, a blank label
    (`a@b..co`, `a@.co`) and a non-string. The message shows the value as received.
  - `UserPassword` accepts exactly 12 characters and rejects 11. The message and the `repr` never
    contain the value.
- [x] `test_user.py`: `create` keeps the fields, records no event, and the primitives round-trip.
- [x] `application/create/test_user_creator.py`, with fakes and a `FixedClock`:
  - The stored user has the normalized email, `hashed:<password>` and `created_at` equal to now.
  - A duplicate email raises `UserAlreadyExists`.
  - An invalid email or a short password raises before anything is hashed or saved.
- [x] `tests/contexts/cms/users/fakes/test_in_memory_user_repository.py`: duplicate email and find
  by email.
- [x] `infrastructure/test_argon2_password_hasher.py`:
  - It verifies its own hash and rejects a wrong password.
  - The hash is not the password.
  - `verify(x, None)` is `False`.
- [x] `infrastructure/persistence/mongo/test_mongo_user_repository.py` (integration):
  - Save, then find by email.
  - An unknown email gives `None`.
  - A duplicate email raises `UserAlreadyExists` and leaves only one document.
  - An invalid stored user raises `InvalidStoredUser`.
  - `created_at` is a BSON date.
- [x] `versions/test_m0003_users_indexes.py`: `email_unique` exists, is unique, and rejects a second
  document with the same email. `test_migrations_list.py` lists `m0003`.
- [x] `tests/apps/cms_backend/test_cli.py` (integration, fresh database):
  - **Success:** the admin is created on an empty database, with the email from `--email` or from
    the prompt. It prints `Admin <admin@example.com> created` and exits 0.
  - **Failures, exit 1 with nothing stored:** passwords that differ, a short password, an invalid
    email, and a second run with the same email (`User with email <admin@example.com> already
    exists`).
  - The password never appears in the captured stdout or stderr.
- [x] `test_main.py`: `daily-trends-py` with no arguments still starts the API (existing tests,
  updated to `main(migrations=...)`).

### Implementation

Notes from implementing it:

- `MongoRepository` also gained `_find_one(query)`, which `find_by_email` uses.
- `MotherCreator` gained `email()` and `password()`.
- Additional mothers: `UserPasswordHashMother` and `UserCreatedAtMother`.
- `UserPassword` checks only the length. It is built from typed strings (the CLI and the use
  case), never from stored data.
- `test_cli.py` also runs the real entry point in a subprocess
  (`main()` → `create-admin --email …`). Without a terminal, `getpass` reads the passwords from
  standard input.


- [x] `uv add pyjwt "pwdlib[argon2]"`.
- [x] Add the domain value objects, `User`, the errors and the ports.
- [x] Add `UserCreator`.
- [x] Add `Argon2PasswordHasher`.
- [x] Add `unique_key` to `_insert`, then `MongoUserRepository` and `InvalidStoredUser`.
- [x] Add `m0003_users_indexes` and append it to `MIGRATIONS`.
- [x] Add `UsersProvider`, register it in `create_container` and extend `STARTUP_DEPENDENCIES`.
- [x] Add `cli.create_admin` and the argparse dispatch in `main`.
- [x] Add the import-linter contract.
- [x] Add `README.md`: how to create an admin.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Log in

Settings, signed tokens, the 401 error kind and `POST /auth/login`. The feed routes are still
public.

### Public contracts

- `contexts/cms/shared/domain/unauthorized_error.py`: `UnauthorizedError(Exception)`.
- `contexts/cms/users/domain`:
  - **Errors, all `UnauthorizedError`:**
    - `InvalidCredentials`: `Invalid email or password`.
    - `InvalidAccessToken`: `Invalid or expired access token`.
    - `MissingAccessToken`: `Authentication required`. It is raised by the app in phase 3.
  - `AccessToken`: frozen, with `value: str` (`repr=False`) and `expires_in_seconds: int`.
  - `AccessTokenIssuer(Protocol)`: `issue(user_id: UserId) -> AccessToken`.
  - `AccessTokenVerifier(Protocol)`: `verify(token: str) -> UserId`, which raises
    `InvalidAccessToken`.
- `contexts/cms/users/application/authenticate/user_authenticator.py`:
  - `UserAuthenticator(repository, hasher, issuer)`.
  - `async execute(*, email: str, password: str) -> AccessToken`. An email that `UserEmail`
    rejects counts as unknown.
  - An unknown email calls `verify(password, None)`. An unknown email and a wrong password both
    raise `InvalidCredentials`.
- `contexts/cms/users/infrastructure/tokens/jwt_access_tokens.py`:
  - `JwtAccessTokens(secret_key: str, ttl: timedelta, clock: Clock)` implements both ports.
  - Claims are `sub`, `iat` and `exp`, signed with HS256.
  - Verification follows the rules in Context.
- `apps/cms_backend/settings.py`:
  - **Fields:** `auth_secret_key: SecretStr` and
    `auth_token_ttl_seconds: int = Field(default=28800, gt=0)`.
  - **Default:** the dev/test default is a fixed value. In production the key is required:
    `AUTH_SECRET_KEY is required when ENV is production`.
  - **Length:** fewer than 32 characters fails in every ENV with
    `AUTH_SECRET_KEY must have at least 32 characters`.
  - The value is never echoed.
- `apps/cms_backend/errors.py`: `UnauthorizedError` maps to 401 with
  `WWW-Authenticate: Bearer`.
- `apps/cms_backend/routes/auth.py`:
  - `router = APIRouter(route_class=JsonBodyRoute, tags=["auth"])`.
  - `POST /auth/login`:
    - **Body:** `LoginRequest {email: str, password: str}`, strict and required.
    - **200:** `AccessTokenResponse {access_token: str, token_type: Literal["bearer"],
      expires_in: int}`.
    - **Errors:** declares 400, 401 and 500 with `ErrorResponse`.
  - `register_routes` includes it.
- `providers/users.py`:
  - Adds `JwtAccessTokens` as `AccessTokenIssuer` and `AccessTokenVerifier`, built from the
    settings and the `Clock`.
  - Adds `UserAuthenticator` to `USER_USE_CASES`.
- `main.DESCRIPTION` mentions the 401.
- Tests: `FakeAccessTokens` (token `token-for:<id>`).

### Tests first

- [ ] `test_user_authenticator.py`:
  - Valid credentials give the issued token for the user's id.
  - Mixed-case or padded email input still logs in.
  - A wrong password raises `InvalidCredentials`, and so does an unknown email, which records
    `verify(password, None)`.
  - An invalid email raises `InvalidCredentials` and still verifies once.
  - Both failures have the same message.
- [ ] `test_jwt_access_tokens.py`:
  - **Round trip:** an issued token verifies back to the user id.
  - **Claims:** `iat`/`exp` come from the clock and `exp - iat == ttl`; `expires_in_seconds == ttl`.
  - **Expiry:** valid at `exp - 1s`, rejected at `exp`.
  - **Rejected, always as `InvalidAccessToken`:**
    - a token signed with another key, or with one character changed;
    - `alg: none`, or signed with HS512;
    - no `sub`, a `sub` that is not a UUID, or no `exp`;
    - garbage text.
- [ ] `test_settings.py`:
  - **Defaults:** the dev/test key and TTL 28800 apply.
  - **Required key:** production without the key fails naming `AUTH_SECRET_KEY`.
  - **Key length:** a 20-character key fails in production and in dev, and 32 characters pass.
  - **TTL:** `AUTH_TOKEN_TTL_SECONDS=0` or `-1` fails.
  - The secret never appears in the error.
- [ ] `test_main.py`: `ENV=production` with `MONGO_URL` set and no `AUTH_SECRET_KEY` exits 1 and
  names `AUTH_SECRET_KEY`.
- [ ] `test_errors.py`: an `UnauthorizedError` answers 401 `{"error": …}` with
  `WWW-Authenticate: Bearer`.
- [ ] `tests/apps/cms_backend/test_login.py` (integration, a user stored with the real hasher):
  - **200:**
    - The body has `token_type: bearer` and `expires_in` equal to the setting.
    - The returned `access_token` passes the app's verifier.
    - It works after the user was created as `Admin@Example.com` and logs in as
      `admin@example.com`.
  - **401, same body every time:**
    - wrong password, unknown email and `email: "not-an-email"` all give
      `{"error": "Invalid email or password"}`;
    - each carries `WWW-Authenticate: Bearer`.
  - **400:**
    - `{"email": "a@b.co"}` answers `password: Field required`;
    - a non-string `password` or a body that is not JSON also gives 400.
- [ ] `test_openapi.py`:
  - `/auth/login` is listed under the `auth` tag with 400, 401 and 500.
  - `test_lists_every_route` includes `/auth/login`.

### Implementation

- [ ] Add `UnauthorizedError` and its mapping with the header in `errors.py`.
- [ ] Add the auth errors, `AccessToken` and the token ports.
- [ ] Add `UserAuthenticator`.
- [ ] Add `JwtAccessTokens`.
- [ ] Add the settings fields and validation.
- [ ] Add the provider wiring.
- [ ] Add `routes/auth.py` and its schemas, and register it.
- [ ] Add `.env.example` entries for `AUTH_SECRET_KEY` and `AUTH_TOKEN_TTL_SECONDS`, with the
  key-generation command.
- [ ] Add `README.md`: how to log in and use the token, and the new settings.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Phase 3: Protect the write routes

The feed write routes and `/feed/scrap` require the bearer token, checked before anything else.

### Public contracts

- `apps/cms_backend/http/authentication.py`:
  - `BEARER = HTTPBearer(auto_error=False, scheme_name="bearer")`.
  - `async authenticate(request: Request) -> UserId`:
    - It raises `MissingAccessToken` when `await BEARER(request)` is `None`.
    - Otherwise it calls `AccessTokenVerifier.verify`, resolved from the request's dishka
      container.
- `apps/cms_backend/http/admin_route.py`: `AdminRoute(JsonBodyRoute)`. Its handler runs
  `authenticate(request)` before `JsonBodyRoute`'s body rules and before FastAPI reads the body.
- `apps/cms_backend/routes/feed.py`:
  - **New router:** `admin_router = APIRouter(route_class=AdminRoute, tags=["feeds"],
    dependencies=[Security(BEARER)])`.
  - **Moved to it:** `GET /feed/scrap`, `PUT /feed/{id}`, `PATCH /feed/{id}` and
    `DELETE /feed/{id}`. Their bodies, statuses and errors do not change.
  - **Public:** `/feed/list`, `/feed/home` and `GET /feed/{id}` stay on `router`.
  - **401 response:** each protected route declares it with `ErrorResponse`, described as
    "Missing, invalid or expired access token".
- `register_routes` includes `status`, `auth`, `feed.admin_router` and then `feed.router`.
- OpenAPI:
  - `components.securitySchemes.bearer = {"type": "http", "scheme": "bearer"}`.
  - `security: [{"bearer": []}]` appears on exactly the 4 protected operations.
- Test harness (`tests/apps/cms_backend/conftest.py`):
  - `client` sends `Authorization: Bearer <valid token>` by default and clears `users`.
  - `anonymous_client` is the same client without the header.
  - `access_token_for(client, container, user_id, *, at=None) -> str` issues tokens for the 401 and
    expiry tests.

### Tests first

- [ ] `tests/apps/cms_backend/test_authentication.py`, parametrized over the 4 protected routes:
  - **"Authentication required" 401:**
    - no header, an empty header, `Basic YWRtaW46c2VjcmV0` and `Bearer` with no token;
    - each carries `WWW-Authenticate: Bearer`.
  - **"Invalid or expired access token" 401:**
    - a token signed with another key, a changed character, and an expired token (issued with a
      clock moved back by more than the TTL);
    - each carries the same header.
  - The scheme `bearer` in lowercase is accepted.
  - A valid token gives today's behavior: 201, 200, 204 and 200.
- [ ] Order and side effects:
  - `PUT /feed/{id}` without a token answers 401 for an invalid field, for malformed JSON and for a
    `text/plain` content type.
  - `DELETE` of a missing feed without a token answers 401.
  - `PATCH` with an invalid id without a token answers 401.
  - `GET /feed/scrap` without a token answers 401, and `front_pages_transport.requests` stays
    empty.
- [ ] Public routes without a token: `/feed/list`, `/feed/home`, `GET /feed/{id}`, `/status`,
  `/docs`, `/redoc` and `/openapi.json` all answer as today.
- [ ] `test_openapi.py`:
  - The bearer scheme is declared.
  - `security` is on exactly the protected operations, and no other has it.
  - The protected routes add `401` to the expected error statuses.
- [ ] Existing HTTP tests and BDD features pass unchanged through the authenticated `client`.
  `test_json_body_route.py` and `test_errors.py` keep working: they use their own routers or an
  authenticated client.

### Implementation

- [ ] Add `authentication.py` and `AdminRoute`.
- [ ] Split `feed.py` into `admin_router` and `router`, and set the registration order.
- [ ] Add the 401 descriptions in `_ERROR_DESCRIPTIONS`.
- [ ] Add the authenticated `client` fixture and `anonymous_client`.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Phase 1 is implemented and waiting for review. After it is approved, run
`/ai-project-implement-phase` in `/Users/ivanpersonal/Repos/daily-trends-py-s11-auth` to implement
Phase 2.
