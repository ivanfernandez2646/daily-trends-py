# S03 · List feeds

**Status:** draft · **Fidelity:** exact. Depends on S02.

## Goal
Return all feeds, most recent first. This spec also defines the search criteria used by the front page (S07).

## Criteria
`filter`: list of conditions combined with OR (each field=value); `sort`: field → `asc|desc`; `limit`: integer (0 or absent = no limit). Without criteria everything is returned.
- In Mongo: filter → `$or`, sort and limit as given. Ordering is **textual** over the ISO strings.

> **Superseded by [I05](../improvements/I05-criteria-and-native-dates.md):** criteria are a domain value object with `filters` (OR), an optional `order` and an optional positive `limit` (absent = no limit), using domain field names (`created_at`). No filters is the only way to search every feed. A limit of 0 or less, or an unknown field, raises `InvalidArgumentError` when the criteria are built.

## `GET /feed/list`
- 200 with an array of all feeds (any source), sorted by `createdAt` descending. No filter. Empty → `[]`.

> **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** an invalid stored feed answers 500 with `Stored feed <{id}> is invalid: {reason}`.


## Acceptance criteria
- Repository integration test: sort, limit, OR filter.
- Cover the `list` `.feature` file.
