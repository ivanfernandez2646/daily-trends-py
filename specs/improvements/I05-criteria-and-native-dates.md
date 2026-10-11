# I05 · Search criteria and native dates

**Status:** draft · **Fidelity:** intentional break with the ported behavior. Depends on S02, S03,
S07, I01, I02 and I04. Resolves improvements #10 and #12 from `README.md`.

## Goal
Search criteria become an explicit domain type that speaks domain field names and has one
meaning for "no filter". Feed dates are stored as native Mongo dates, so ordering and day ranges
are chronological instead of textual. The HTTP contract does not change.

## Changes

### Criteria (#10)
Today `Criteria` is a dictionary shaped like a Mongo query. Its conditions use storage field names
(`createdAt`), an empty `$or` is avoided only by a guard in the repository, `limit: 0` means "no
limit", and the in-memory fake ignores the criteria completely.

- `Criteria` is a domain value object with:
  - `filters`: zero or more **field equals value** conditions, combined with OR (as in S03).
    **No filters** means every feed. It is the only way to say that.
  - `order`: an optional field and a direction (`asc` | `desc`).
  - `limit`: an optional positive integer. **Absent** means no limit.
- Fields are domain names (`source`, `created_at`, …). The Mongo feed repository maps them to
  storage names. Code outside the repository never names a storage field.
- Invalid criteria fail when they are built, with `InvalidArgumentError`: a limit of 0 or less, or
  a field the feed does not have. Criteria are built only by code, never from a request, so these
  errors are programming errors and answer 500 if they ever reach a route.
- The in-memory fake repository applies filters, order and limit. Use-case tests can then check
  results instead of the criteria object they passed.
- The two existing uses keep their meaning: `/feed/list` orders by `created_at` descending with no
  filter and no limit, and the home criteria filter `EL_MUNDO` OR `EL_ESPANOL`, order by `created_at`
  descending and limit 10 (S07).

### Native dates (#12)
- `createdAt` and `updatedAt` are stored as BSON dates (UTC, millisecond precision) instead of
  ISO-8601 strings. `updatedAt: null` stays `null`.
- Sorting by `createdAt` is chronological. Before this change it compared text, so a date stored
  with an offset (`+02:00`) sorted wrongly against `Z` dates.
- The scraping day range (I02, with the business day from I04) is a range of dates.
- Responses do not change: dates are still returned as ISO-8601 UTC with milliseconds and `Z` (S02).
- A stored date that is not a BSON date (a string, a number, a missing `createdAt`) is an invalid
  stored feed and answers 500 (I01) with
  `Stored feed <{id}> is invalid: <FeedCreatedAt> does not allow the value <{value}>`.

### No data migration
- There is no data to keep: every environment starts with an empty `feeds` collection. No
  migration command is provided, and documents written by an earlier version are not supported.

## Unchanged
- `/feed/list` and `/feed/home` responses, ordering direction, the home limit, and the rule that
  `CMS` feeds never appear on the home page (S03, S07).
- The JSON shape of a feed and its date format in every response (S02).
- Deduplication, cooldown and single-flight rules (I02, I03) other than how the day range is
  stored and queried.
- Everything in `README.md` outside #10 and #12.

## Edge cases
- `Criteria` with no filters, no order and no limit → every feed, in storage order.
- `Criteria` with `limit=0` → `InvalidArgumentError` when it is built.
- Two feeds created at `2026-10-09T10:00:00+02:00` (08:00 UTC) and `2026-10-09T09:30:00Z`. The
  second one is newer and sorts first on `/feed/list`. As text, the first one sorted first.
- A stored document with `createdAt: "not-a-date"` or any other string → every route that reads it
  answers 500 (I01).

## Acceptance criteria
- Unit tests for `Criteria`: no filters, OR filters, order, a missing limit, invalid limits, unknown
  fields.
- The in-memory fake honours criteria, and use-case tests for `/feed/list` and `/feed/home` assert
  results.
- Mongo repository integration tests: dates stored as BSON dates, chronological sort across
  offsets, the OR filter, a missing limit, the business-day range, and the invalid stored date
  error for a string date.
- `list-feed.feature` and `home-feed.feature` pass unchanged.
- `S02-create-and-find-feed.md` ("dates are stored as ISO-8601 strings") and `S03-list-feeds.md`
  ("ordering is textual", the criteria shape) get a "Superseded by I05" note. `README.md` links I05
  for #10 and #12.
