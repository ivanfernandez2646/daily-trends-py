# Known improvements (do NOT implement in the migration)

Each item is current behavior that the port **keeps**, with the proposed improvement. They are tackled later as their own specs (`I0N-*.md`); the **Spec** column links the one that resolves each item.

| # | Current defect | Where | Proposed improvement | Spec |
|---|---|---|---|---|
| 1 | Per-environment config (`dev.json`/`test.json`) is never loaded | S01 | Load per environment / `.env` | [I04](I04-configuration.md) |
| 2 | Duplicate feed returns 302 without `Location` | S01/S02 | 409 Conflict | [I01](I01-http-contract-fixes.md) |
| 3 | Every scraping run re-inserts the same headlines | S06 | Deduplicate by source + title + day | [I02](I02-scraper-robustness.md) |
| 4 | If scrapers fail, the front page retries on every request | S07 | Cooldown or scheduled job | [I03](I03-background-front-page-scraping.md) |
| 5 | Scraping runs inline inside an HTTP request | S07 | Background job | [I03](I03-background-front-page-scraping.md) |
| 6 | "Id already exists, regenerate" loop with no practical effect | S06 | Remove | [I02](I02-scraper-robustness.md) |
| 7 | `PATCH` with `title: ""` is ignored, `"  "` gives 400, `description: ""` is accepted | S04 | Unify validation | [I01](I01-http-contract-fixes.md) |
| 8 | El Mundo always iso-8859-1 and last description character trimmed; no timeout or User-Agent, so a site that never answers also hangs `/feed/home` | S06/S07 | Detect charset, timeout, document trimming | [I02](I02-scraper-robustness.md) |
| 9 | Scraper stores description `""` instead of `null` | S06 | Normalize to `null` | [I02](I02-scraper-robustness.md) |
| 10 | Empty or missing `$or` filter is fragile | S03 | Rewrite criteria | [I05](I05-criteria-and-native-dates.md) |
| 11 | `DELETE` and `/feed/scrap` answer 200 empty | S05/S06 | 204 / scraping result | [I01](I01-http-contract-fixes.md) |
| 12 | Dates ordered as text | S02/S03 | Native date types in Mongo | [I05](I05-criteria-and-native-dates.md) |
| 13 | Events without subscribers and an unused deserializer | S02 | Decide whether the bus stays | Kept: subscribers arrive in a later feature |
| 14 | CI on Node 14/15 and Dockerfile without `CMD` | S01 | Already solved in the port | |
| 15 | No authentication or pagination on `/feed/list` | S03 | Out of scope for now | |
| 16 | Date-time validation errors name `<Function>` instead of the value object | S02 | Use the class name | [I01](I01-http-contract-fixes.md) |
| 17 | Concurrent `/feed/home` requests on a stale day each run the scraping and store duplicate batches | S07 | Single-flight lock, or solved by #5 | [I03](I03-background-front-page-scraping.md) |
| 18 | "Today" for the front page depends on the server's timezone (`TZ`), usually UTC in containers | S07 | Explicit business timezone in settings | [I04](I04-configuration.md) |
| 19 | A malformed `createdAt` stored in Mongo answers 400 on `/feed/home` (it maps `InvalidArgumentError`) but 500 on `/feed/list`, although the client sent nothing wrong | S03/S07 | Treat invalid stored data as a server error (500) everywhere, or validate on write | [I01](I01-http-contract-fixes.md) |
| 20 | The HTTP layer mirrors the original framework: hand-parsed bodies (JSON and urlencoded), JavaScript-style values in messages (`undefined`, `[object Object]`), untyped `app.state` services, a per-route error wrapper and a hand-written OpenAPI file | S01/S02/S04 | Pydantic request/response models, a dishka DI container, exception handlers, generated OpenAPI | [I06](I06-idiomatic-fastapi-layer.md) |
| 21 | Create checks existence and then upserts, so concurrent `PUT`s with the same id both answer 201 and the last one wins; a `PATCH` racing a `DELETE` brings the feed back | S01/S02/S04 | Insert-only create (duplicate key → 409), update without upsert (no match → 404) | [I08](I08-persistence-and-error-hardening.md) |
| 22 | A 500 returns the internal error message to the client | S01/I01 | Generic 500 body, details only in the log | [I08](I08-persistence-and-error-hardening.md) |
| 23 | The `feeds` collection has no index besides `_id`; listing, front page and deduplication scan it | S03/S07/I02 | Create the indexes as the first migration | [I08](I08-persistence-and-error-hardening.md) |
| 24 | `pytest` hangs without MongoDB: each test waits 30 seconds for the driver | S01 | Short Mongo timeout in tests, one reachability check that fails the session at once | [I08](I08-persistence-and-error-hardening.md) |
| 25 | No way to apply schema changes (indexes, data reshapes) to MongoDB in a versioned, repeatable way | S01 | Versioned migrations applied at startup, once per database | [I07](I07-mongo-migrations.md) |
