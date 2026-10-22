# S04 · Update a feed

**Status:** implemented · **Fidelity:** exact. Depends on S02.

## `PATCH /feed/:id`
- Body: optional `title` and `description`.
- Absence rule:
  - `title` falsy (absent or `""`) → **not changed**, no error.
  - `title` present and non-empty → validated as required (whitespace only → 400).
  - `description` absent → not changed; present (including `null` and `""`) → assigned.

> **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** absent `title` → not changed; any present `title` is validated as in `PUT` (`""`, `null`, `0` → 400).

- Feed missing → 404.

> **Superseded by [I06](../improvements/I06-idiomatic-fastapi-layer.md):** the body is validated by `UpdateFeedRequest` before the feed is looked up. Order of checks: body schema (400, e.g. `title: Input should be a valid string` for `null` or `0`) → id (400) → find (404) → blank title (400). A missing body reads as `{}`.

- If the result is identical to the current feed → return it **without saving or touching `updatedAt`**. If something changes → `updatedAt` = now, save and return it.
- Response 200 with the feed. No event is emitted.
- Any source can be updated.

## Edge cases
- PATCH `{}` → 200 with the unchanged feed.
- PATCH `description: null` on a feed with a description → becomes `null`, `updatedAt` changes.

## Acceptance criteria
- Use-case tests: no changes / changes / 404 / invalid title.
- Cover the `update` `.feature` file.
