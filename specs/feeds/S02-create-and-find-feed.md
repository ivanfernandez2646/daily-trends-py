# S02 · Create and find a feed

**Status:** draft · **Fidelity:** exact. Depends on S01.

## Goal
Create a CMS feed and retrieve it by id. This spec also defines the domain building blocks reused by all later capabilities.

## Domain building blocks
| Type | Rule | Error message (400) |
|---|---|---|
| Optional string | Accepts `null` and any string (even empty) | — |
| Required string | Fails if falsy or only whitespace | `<{ClassName}> is mandatory. Current value: <{value}>` |
| UUID | Required and valid per uuid@9 `validate`: versions 1–5 or the nil UUID (a v7 UUID is invalid) | `<{ClassName}> does not allow the value <{value}>` |
| Optional date-time | `null`/empty valid; otherwise parseable | `<Function> doesn't allow the value <{value}>` (see note) |
| Required date-time | Parseable | same as above |

- Date-time messages always say `<Function>`, not the class name: the original reads `this.constructor.name` inside a static method. Kept as is (improvement #16).
- Values in messages are rendered as JavaScript's `String()` does: an absent field is `undefined`, `null` is `null`, `true`/`false`, `123`, lists joined with `,`.
- `FeedId` = UUID; `FeedTitle` and `FeedAuthor` = required string; `FeedDescription` = optional string.
- Equality by value. The value is **not normalized** (no trim on store).
- Dates are stored as ISO-8601 strings (UTC, milliseconds, `Z`).
- `Feed` fields as in S00. `createdAt` = now on creation; `updatedAt` = `null` until the first effective modification.
- Domain events: base fields `eventId` (UUID), `eventName`, `aggregateId`, `occurredOn`. The aggregate accumulates events; pulling returns and clears them. Only event today: `feed.created` (attribute `title`). An event deserializer exists in the original but is unused: omit it.

## Create — `PUT /feed/:id`
- Input: `id` in the path; `title`, `description` (optional), `author` in the body, sent as JSON (`application/json`) or urlencoded (`application/x-www-form-urlencoded`). Any other content type is read as an empty body.
- `source` is always `CMS`, never read from the body. Missing `description` → `null`.
- Order: validate id, title, description, author (first failure wins) → check duplicate → create, save, publish `feed.created`.
- Existing id → "already exists" error (302). Nothing is modified.

  > **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** an existing id answers 409.

- Response 201 with the feed JSON:
```json
{ "id": "uuid", "title": "string", "description": "string|null", "author": "string",
  "source": "CMS|EL_PAIS|EL_MUNDO|EL_ESPANOL", "createdAt": "ISO-8601", "updatedAt": "ISO-8601|null" }
```
- *Given* a new id and valid title/author, *when* PUT, *then* 201 and the feed is stored with `updatedAt: null`.

## Find — `GET /feed/:id`
- 200 with the feed, or 404 if missing. An invalid UUID → 400.

## Edge cases
- Same id twice in a row: the second → 302.
- Missing body → `title`/`author` undefined → 400 "mandatory".
- Invalid UUID in the path → 400 `<FeedId> does not allow the value <{id}>`.
- Missing `title` → 400 `<FeedTitle> is mandatory. Current value: <undefined>`; `"title": null` → `<null>`.
- A JSON array body has no fields (same as a missing body). An urlencoded key sent twice becomes a list (`title=a&title=b` → `<a,b>`, a 400).

### Deliberate divergences from the original
- **Non-string values** → 400. A non-string `title`/`author` gives `<FeedX> is mandatory. Current value: <{value}>`; a non-string `description` gives `<FeedDescription> does not allow the value <{value}>`. The original answered 500 `value.trim is not a function` for truthy non-strings and stored non-string descriptions as they came.
- **Malformed JSON**, or a JSON body that does not start with an object or array → 400, plain text `Bad Request`. The original answered an HTML 400 page from its framework.

## Acceptance criteria
- Unit tests per value object (valid, invalid, exact messages, equality) and for the aggregate event pull.
- Use-case tests with an in-memory repository (create, duplicate, event published, find, not found).
- Cover the `create` and `find` `.feature` files.
- Repository integration test against real Mongo: upsert and find by id.
