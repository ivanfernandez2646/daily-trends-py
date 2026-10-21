# S13 · Administrator session

**Status:** draft · **Fidelity:** new capability, additive (no existing route changes). Depends on
S11.

## Goal
A client that holds an access token (S11) can ask who it belongs to and until when it is valid, so a
web CMS can show the logged-in administrator, restore a session after a page reload and send the
user back to the login screen before a write fails with 401.

## `GET /auth/me`
- Protected like the write routes of S11: `Authorization: Bearer <token>`, and the same 401 answers,
  bodies and `WWW-Authenticate: Bearer` header for a missing, malformed, wrongly signed or expired
  token.
- 200 with the administrator and the token expiry:

  ```json
  {
    "id": "6b1c7f8e-…",
    "email": "admin@example.com",
    "created_at": "2026-10-21T08:00:00Z",
    "token_expires_at": "2026-10-21T16:00:00Z"
  }
  ```

  - `id`, `email` and `created_at` are the stored user; the date format is that of every response
    (I06).
  - `token_expires_at` is the `exp` claim of the token in the request, as an instant in UTC.
  - The password hash is never part of the response (S11).
- A valid token whose user no longer exists (deleted in Mongo, S11) → 401
  `{"error": "Invalid or expired access token"}`. The client reacts as to an expired token.
- The route is documented in the `auth` OpenAPI tag with the bearer security scheme.

## Domain and application
- The token verifier of S11 answers the user id **and** the expiry of the token. The protected
  routes of S11 keep using only the id.
- A use case finds the user by id through the user repository, which gains `find by id`. A missing
  user raises `InvalidAccessToken` (S11), so `apps/cms_backend` needs no new mapping.
- No change to how tokens are verified on the other routes: they still do not read the database
  (S11).

## Unchanged
- `/auth/login` and its response (S11). The token TTL and the claims.
- There is still no refresh, revocation or logout: logging out is the client forgetting the token.

## Edge cases
- Token issued at `10:00:00` with a TTL of 28800 → `/auth/me` at `12:00` answers
  `token_expires_at: "…T18:00:00Z"`; at `18:00:00` it answers 401.
- No `Authorization` header → 401 `Authentication required`.
- A user deleted after logging in → `/auth/me` answers 401, while the write routes still accept the
  token until it expires (S11).

## Acceptance criteria
- Adapter test: the JWT verifier answers the id and the expiry of a token it issued.
- Use-case tests with fakes: the user and the expiry; a missing user raises `InvalidAccessToken`.
- Repository integration test against real Mongo: find a user by id, and a missing id.
- HTTP tests: 200 with the four fields and no `password_hash`; 401 for every token case of S11 and
  for a deleted user, with `WWW-Authenticate: Bearer`.
- OpenAPI test: `/auth/me` is documented, protected and has a 401 response.
- `S00` lists S13.
- The quality gate from `AGENTS.md` passes.
