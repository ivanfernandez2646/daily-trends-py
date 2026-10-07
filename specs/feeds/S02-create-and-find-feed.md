# S02 · Create and find a feed

**Status:** draft · **Fidelity:** exact. Depends on S01.

## Goal
Create a CMS feed and retrieve it by id. This spec also defines the domain building blocks reused by all later capabilities.

## Domain building blocks
| Type | Rule | Error message (400) |
|---|---|---|
| Optional string | Accepts `null` and any string (even empty) | — |
| Required string | Fails if falsy or only whitespace | `<{ClassName}> is mandatory. Current value: <{value}>` |
| UUID | Required and valid per `uuid.validate` (any version) | `<{ClassName}> does not allow the value <{value}>` |
| Optional date-time | `null`/empty valid; otherwise parseable | `<{ClassName}> doesn't allow the value <{value}>` |
| Required date-time | Parseable | same as above |

- `FeedId` = UUID; `FeedTitle` and `FeedAuthor` = required string; `FeedDescription` = optional string.
- Equality by value. The value is **not normalized** (no trim on store).
- Dates are stored as ISO-8601 strings (UTC, milliseconds, `Z`).
- `Feed` fields as in S00. `createdAt` = now on creation; `updatedAt` = `null` until the first effective modification.
- Domain events: base fields `eventId` (UUID), `eventName`, `aggregateId`, `occurredOn`. The aggregate accumulates events; pulling returns and clears them. Only event today: `feed.created` (attribute `title`). An event deserializer exists in the original but is unused: omit it.

## Create — `PUT /feed/:id`
- Input: `id` in the path; `title`, `description` (optional), `author` in the body.
- `source` is always `CMS`, never read from the body. Missing `description` → `null`.
- Order: validate id, title, description, author (first failure wins) → check duplicate → create, save, publish `feed.created`.
- Existing id → "already exists" error (302). Nothing is modified.
- Response 201 with the feed JSON:
```json
{ "id": "uuid", "title": "string", "description": "string|null", "author": "string",
  "source": "CMS|EL_PAIS|EL_MUNDO", "createdAt": "ISO-8601", "updatedAt": "ISO-8601|null" }
```
- *Given* a new id and valid title/author, *when* PUT, *then* 201 and the feed is stored with `updatedAt: null`.

## Find — `GET /feed/:id`
- 200 with the feed, or 404 if missing. An invalid UUID → 400.

## Edge cases
- Same id twice in a row: the second → 302.
- Missing body → `title`/`author` undefined → 400 "mandatory".
- Invalid UUID in the path → 400 `<FeedId> does not allow the value <{id}>`.

## Acceptance criteria
- Unit tests per value object (valid, invalid, exact messages, equality) and for the aggregate event pull.
- Use-case tests with an in-memory repository (create, duplicate, event published, find, not found).
- Cover the `create` and `find` `.feature` files.
- Repository integration test against real Mongo: upsert and find by id.
