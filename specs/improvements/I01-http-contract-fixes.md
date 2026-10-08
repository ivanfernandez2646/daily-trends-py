# I01 · HTTP contract fixes

**Status:** draft · **Fidelity:** intentional break with the ported behavior. Depends on S00–S07.
Resolves improvements #2, #7, #11, #16 and #19 from `README.md`.

## Goal
Make the API's status codes and error messages say what happened: a conflict is a conflict, an
empty success is `204`, a scraping run reports what it saved, `PATCH` validates a title the same way
`PUT` does, and data the client never sent can no longer produce a `400`.

## Changes

### Duplicate feed → 409 (#2)
- `PUT /feed/:id` with an existing id → **409 Conflict**, body
  `{"error": "Feed with id <{id}> already exists"}`. Nothing is modified. No `Location` header.
- Replaces the `302` from S01/S02.

### Empty and scraping responses (#11)
- `DELETE /feed/:id` on an existing feed → **204 No Content**, empty body. 404 and 400 unchanged.
- `GET /feed/scrap` → **200** with a JSON array of the feeds saved by this run, in the feed JSON
  shape of S02, in scraper order (El Mundo, then El Español) and article order within each scraper.
  - A failing scraper contributes nothing, as before; if every scraper fails or finds nothing →
    `200` with `[]`.
  - A save error still propagates as 500; feeds saved before it are not rolled back.
- `GET /feed/home` is unchanged: it ignores the scraping result.

### `PATCH` title validation (#7)
- `title` **absent** → not changed.
- `title` **present** → validated exactly as in `PUT` (`FeedTitle`, required string): any non-string
  value or a blank string → 400 `<FeedTitle> is mandatory. Current value: <{value}>`.
  - `""` → `<>`, `"  "` → `<  >`, `null` → `<null>`, `0` → `<0>`.
- `description` is unchanged: absent → not changed; `null` or any string (including `""`) is
  assigned, the same rule as `PUT`.
- Order is unchanged: validate id (400) → find the feed (404) → validate title and description (400).
- Everything else in S04 stays (no save and no `updatedAt` change when nothing changes, no event).

### Date-time errors name the value object (#16)
- New value objects `FeedCreatedAt` (required date-time) and `FeedUpdatedAt` (optional date-time)
  type the feed's `createdAt` and `updatedAt`.
- Message: `<{ClassName}> does not allow the value <{value}>`, e.g.
  `<FeedCreatedAt> does not allow the value <not-a-date>`. Same wording as the UUID error.
- Replaces `<Function> doesn't allow the value <{value}>` from S02.

### Invalid stored data → 500 (#19)
- A stored feed document that a value object rejects (for example a malformed `createdAt` or a blank
  `title` written by something other than this API) is a server error, never a client error.
- Reading it answers **500** on every route that loads feeds: `GET /feed/:id`, `PUT /feed/:id`
  (existence check), `PATCH /feed/:id`, `DELETE /feed/:id`, `GET /feed/list`, `GET /feed/home`.
  Body: `{"error": "Stored feed <{id}> is invalid: {reason}"}`, where `{reason}` is the value
  object's message.
- `GET /feed/home` no longer maps any error to 400: it has no client input.
- Client input errors keep their 400 (an invalid UUID in the path, an invalid body field).

## Unchanged
- Error body format `{"error": "<message>"}` and the 404 message.
- Everything in `README.md` outside #2, #7, #11, #16 and #19 (scraping duplicates, the id-regeneration
  loop, `""` descriptions from scrapers, text ordering of dates, and so on).

## Edge cases
- `PATCH {"title": null}` on an existing feed → 400 `<FeedTitle> is mandatory. Current value: <null>`
  (it was ignored before).
- `PATCH {"title": ""}` on a missing feed → 404 (the feed is found before the title is validated).
- `GET /feed/scrap` with one failing source → 200 with only the other source's feeds.
- A malformed stored `createdAt` among other valid feeds → `/feed/list` and `/feed/home` answer 500.

## Acceptance criteria
- Ported `.feature` files updated: `create` (409), `delete` (204), `scrap` (`/feed/scrap` returns an
  array of length 10 instead of an empty body).
- Use-case tests: the scraper returns the saved feeds (including when a scraper fails); the updater
  rejects `""`, `null` and `0` titles and keeps ignoring an absent title.
- Value-object tests: `FeedCreatedAt` and `FeedUpdatedAt` messages name the class.
- Repository integration test against real Mongo: a malformed stored document raises the
  invalid-stored-feed error on `find` and `search`.
- Acceptance tests for each route listed under #19 answering 500 for a malformed stored document.
- `docs/openapi.yml` documents 409, 204, the scraping array and a 500 for invalid stored data.
