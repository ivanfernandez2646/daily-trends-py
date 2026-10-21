---
name: 's13-admin-session'
description: 'GET /auth/me answers the administrator behind a bearer token and when the token expires, and 401 for a deleted user'
spec: 'specs/users/S13-admin-session.md'
branch: 'feat/s13-admin-session'
created_at: '2026-10-21T10:59:42Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-21T11:40:00Z'
implemented_at: '2026-10-21T11:40:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S13 · Administrator session

## Goal

A client with an access token calls `GET /auth/me` and gets the stored administrator (`id`, `email`,
`created_at`) and the token's `exp` as `token_expires_at`. The endpoint answers the same 401s as the
S11 write routes. A token whose user no longer exists answers 401 `Invalid or expired access token`.
The write routes do not change, and they still never read the database to verify a token.

## Context

- **Verifier:** `AccessTokenVerifier.verify(token) -> UserId` is called only by
  `apps/cms_backend/http/authentication.py` and by tests (`test_jwt_access_tokens.py`,
  `test_login.py`). Its return type changes to a `VerifiedAccessToken` that also carries the
  expiry. `AdminRoute` ignores what `authenticate` returns, so the write routes keep using only the
  id.
- **Agreed:** the use case receives a `VerifiedAccessToken`, not the raw token. `/auth/me` verifies
  the token with the same `authenticate()` as the write routes, so its 401 answers match theirs by
  construction. The use case only looks up the user.
- **Route mechanics:** `/auth/me` has no body, so a `Depends(authenticate)` parameter runs before
  anything else that could fail. That means it needs no `AdminRoute`. The route declares
  `dependencies=[Security(BEARER)]` so OpenAPI marks it as protected. It stays on the `auth`
  router (`JsonBodyRoute`, tag `auth`).
- **Errors:** a missing user raises `InvalidAccessToken`, which is an `UnauthorizedError`. That kind
  already maps to 401 with `WWW-Authenticate: Bearer`, so `errors.py` does not change.
- **Dates:** `created_at` and `token_expires_at` are `datetime` fields of a Pydantic response, the
  same as `FeedResponse`, so they serialize the same way (I06).
- **Repository:** `UserRepository` gains `find_by_id`. `MongoUserRepository` queries `{"_id": id}`
  and reuses `_to_user`, so a broken document raises `InvalidStoredUser` (500) just as
  `find_by_email` does. `InMemoryUserRepository` is keyed by email, so its lookup by id scans the
  values.
- **HTTP fixtures:** the `client` fixture sends a token for a random user that is never stored.
  That is enough for the write routes, but `/auth/me` would answer 401 with it. The `/auth/me`
  tests store a user through the app's `UserRepository` and send a token issued for that user.
- **Already done:** S00 already lists S13. `test_openapi.py` lists every route
  (`test_lists_every_route`) and the exact set of secured operations (`PROTECTED_OPERATIONS`), so
  both get `/auth/me`.
- **Worktree:** this plan is implemented in the worktree `.claude/worktrees/s13-admin-session`
  while S12 is developed in the main checkout. S12 and S13 touch different files, except for
  `tests/apps/cms_backend/test_openapi.py` and the README API table, where a merge conflict is
  possible.

## Phases

## Phase 1: Administrator session

The whole feature in one vertical slice: the verifier answers the expiry, the repository finds
users by id, the use case builds the session, and `GET /auth/me` exposes it in the API and in
OpenAPI.

### Public contracts

- `contexts/cms/users/domain/verified_access_token.py`:

  ```python
  @dataclass(frozen=True)
  class VerifiedAccessToken:
      """A token whose signature and expiry were checked: who it is for and until when."""

      user_id: UserId
      expires_at: datetime  # UTC
  ```

- `AccessTokenVerifier.verify(self, token: str) -> VerifiedAccessToken`. It still raises
  `InvalidAccessToken` otherwise.
- `JwtAccessTokens.verify` returns `VerifiedAccessToken(UserId(sub), datetime.fromtimestamp(exp, UTC))`.
- `UserRepository.find_by_id(self, id: UserId) -> User | None`.
- `contexts/cms/users/application/find_session/admin_session_finder.py`:

  ```python
  @dataclass(frozen=True)
  class AdminSession:
      user: User
      token_expires_at: datetime


  class AdminSessionFinder:
      def __init__(self, repository: UserRepository) -> None: ...

      async def execute(self, token: VerifiedAccessToken) -> AdminSession:
          """Raises `InvalidAccessToken` when the token's user no longer exists."""
  ```

- `apps/cms_backend/http/authentication.py`: `async def authenticate(request: Request) -> VerifiedAccessToken`.
- `apps/cms_backend/providers/users.py`: `admin_session_finder = provide(AdminSessionFinder)`, and
  `USER_USE_CASES = (UserCreator, UserAuthenticator, AdminSessionFinder)`.
- `apps/cms_backend/routes/auth_schemas.py`:

  ```python
  class AdminSessionResponse(BaseModel):
      id: str
      email: str
      created_at: datetime
      token_expires_at: datetime

      @classmethod
      def from_admin_session(cls, session: AdminSession) -> Self: ...
  ```

- HTTP: `GET /auth/me`, tag `auth`, security `[{"bearer": []}]`.
  - 200: `AdminSessionResponse`.
  - 401 and 500: `ErrorResponse`.
  - Docstring: "The administrator behind the bearer access token, and when the token expires."
- Test doubles:
  - `FakeAccessTokens(expires_in_seconds=3600, expires_at=<fixed UTC datetime>)`. `verify` returns
    `VerifiedAccessToken(UserId(...), expires_at)`.
  - `InMemoryUserRepository.find_by_id`.

### Tests first

- [x] `test_jwt_access_tokens.py`:
  - A token verifies back to its user and to `exp` as a UTC instant. For example, issued at
    `10:00:00` with a TTL of 28800, it verifies to `18:00:00+00:00`.
  - Adapt `test_a_token_verifies_back_to_the_user_it_was_issued_for` to read `.user_id`.
- [x] `test_in_memory_user_repository.py`: the fake finds a created user by id, and answers `None`
  for an unknown id.
- [x] `test_mongo_user_repository.py` (integration, real Mongo):
  - `find_by_id` finds a created user.
  - It answers `None` for an unknown id.
  - It raises `InvalidStoredUser` for a broken document.
- [x] `tests/contexts/cms/users/application/find_session/test_admin_session_finder.py`:
  - An existing user gives an `AdminSession` with that user and the token's `expires_at`.
  - A missing user raises `InvalidAccessToken`.
- [x] `tests/apps/cms_backend/test_admin_session.py` (integration):
  - A stored administrator with a token issued now, with the app's key and TTL, answers 200 with
    exactly `id`, `email`, `created_at` and `token_expires_at`. The dates use the API format, and
    there is no `password_hash`.
  - The S11 token cases answer 401 with `WWW-Authenticate: Bearer`:
    - no header, or a non-bearer `Authorization`: `Authentication required`;
    - a token signed with another key, a changed token or an expired token:
      `Invalid or expired access token`.
  - A valid token for a user deleted from the `users` collection answers 401
    `Invalid or expired access token`.
  - The same token still passes authentication on a write route (S11): for example,
    `DELETE /feed/{unknown id}` answers 404, not 401.
- [x] `test_login.py`: adapt the `verifier.verify(...)` assertion to `.user_id`.
- [x] `test_openapi.py`:
  - Add `/auth/me: ["get"]` to `test_lists_every_route`.
  - Add `("/auth/me", "get")` to `PROTECTED_OPERATIONS`.
  - `/auth/me` is under the `auth` tag. Its 200 references `AdminSessionResponse`, and its 4xx/5xx
    are exactly `{"401", "500"}` as `ErrorResponse`.
  - `AdminSessionResponse` lists `id`, `email`, `created_at`, `token_expires_at`, in that order,
    with `date-time` formats.

### Implementation

Notes from implementing it:

- **S11 token cases:** `/auth/me` joined `PROTECTED` in `test_authentication.py`, so every S11 401
  case (no header, other schemes, another key, a changed token, an expired token) runs against it.
  `test_admin_session.py` covers only the 200 and the deleted user.
- **Expiry in the 200 test:** the token is issued with the app's key and TTL and a `FixedClock` set
  to now, truncated to the second, so `token_expires_at` is known exactly.
- **Mongo `find_by_id`:** the broken-document case is a single test with a blank password hash. An
  invalid `_id` cannot be looked up through a `UserId`.
- **Docs:** the README API table and the OpenAPI description mention `/auth/me`.

- [x] Add `VerifiedAccessToken`, and change `AccessTokenVerifier` and `JwtAccessTokens.verify`.
- [x] Update `FakeAccessTokens` and `authenticate()`. `AdminRoute` stays unchanged.
- [x] Add `find_by_id` to `UserRepository`, `MongoUserRepository` and `InMemoryUserRepository`.
- [x] Add `AdminSessionFinder` and `AdminSession`, and register them in `UsersProvider` and
  `USER_USE_CASES`.
- [x] Add `AdminSessionResponse`, and the `GET /auth/me` route on the `auth` router with
  `Security(BEARER)`, `Depends(authenticate)` and the 401/500 responses.
- [x] In the README API table, add `GET /auth/me` marked as protected. If the OpenAPI description
  lists the routes that need a token, add it there too.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Every phase is implemented. After Phase 1 is reviewed and committed in the worktree, rebase
`feat/s13-admin-session` on `main` once S12 is merged. Expect conflicts in `test_openapi.py` and in the
README API table. Then open the pull request.
