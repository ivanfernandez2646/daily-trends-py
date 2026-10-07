# S03 · List feeds

**Status:** draft · **Fidelity:** exact. Depends on S02.

## Goal
Return all feeds, most recent first. This spec also defines the search criteria used by the front page (S07).

## Criteria
`filter`: list of conditions combined with OR (each field=value); `sort`: field → `asc|desc`; `limit`: integer (0 or absent = no limit). Without criteria everything is returned.
- In Mongo: filter → `$or`, sort and limit as given. Ordering is **textual** over the ISO strings.

## `GET /feed/list`
- 200 with an array of all feeds (any source), sorted by `createdAt` descending. No filter. Empty → `[]`.

## Acceptance criteria
- Repository integration test: sort, limit, OR filter.
- Cover the `list` `.feature` file.
