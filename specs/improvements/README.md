# Known improvements (do NOT implement in the migration)

Each item is current behavior that the port **keeps**, with the proposed improvement. They are tackled later as their own specs.

| # | Current defect | Where | Proposed improvement |
|---|---|---|---|
| 1 | Per-environment config (`dev.json`/`test.json`) is never loaded | S01 | Load per environment / `.env` |
| 2 | Duplicate feed returns 302 without `Location` | S01/S02 | 409 Conflict |
| 3 | Every scraping run re-inserts the same headlines | S06 | Deduplicate by source + title + day |
| 4 | If scrapers fail, the front page retries on every request | S07 | Cooldown or scheduled job |
| 5 | Scraping runs inline inside an HTTP request | S07 | Background job |
| 6 | "Id already exists, regenerate" loop with no practical effect | S06 | Remove |
| 7 | `PATCH` with `title: ""` is ignored, `"  "` gives 400, `description: ""` is accepted | S04 | Unify validation |
| 8 | El Mundo always iso-8859-1 and last description character trimmed; no timeout or User-Agent, so a site that never answers also hangs `/feed/home` | S06/S07 | Detect charset, timeout, document trimming |
| 9 | Scraper stores description `""` instead of `null` | S06 | Normalize to `null` |
| 10 | Empty or missing `$or` filter is fragile | S03 | Rewrite criteria |
| 11 | `DELETE` and `/feed/scrap` answer 200 empty | S05/S06 | 204 / scraping result |
| 12 | Dates ordered as text | S02/S03 | Native date types in Mongo |
| 13 | Events without subscribers and an unused deserializer | S02 | Decide whether the bus stays |
| 14 | CI on Node 14/15 and Dockerfile without `CMD` | S01 | Already solved in the port |
| 15 | No authentication or pagination on `/feed/list` | S03 | Out of scope for now |
| 16 | Date-time validation errors name `<Function>` instead of the value object | S02 | Use the class name |
| 17 | Concurrent `/feed/home` requests on a stale day each run the scraping and store duplicate batches | S07 | Single-flight lock, or solved by #5 |
| 18 | "Today" for the front page depends on the server's timezone (`TZ`), usually UTC in containers | S07 | Explicit business timezone in settings |
