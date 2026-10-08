---
name: 's03-list-feeds'
description: 'Criteria-based feed search and GET /feed/list returning all feeds, newest first'
spec: 'specs/feeds/S03-list-feeds.md'
branch: 'feat/s03-list-feeds'
created_at: '2026-10-08T09:21:24Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S03 · List feeds

## Goal

Return every feed with `GET /feed/list`, sorted by `createdAt` descending, with the same status code
and body as the Node reference. This plan also adds the search criteria (`filter` OR list, `sort`,
`limit`) and the `FeedSearcher` use case that S07 (`/feed/home`) reuses. The repository stays green.

## Context

S02 delivered the `Feed` aggregate (`to_primitives`/`from_primitives`, ISO-string dates),
`FeedRepository` (`save`, `find`), `MongoRepository` (`_persist`, `_by_id`, `_remove`),
`MongoFeedRepository` (collection `feeds`), `routes/feed.py` with `run_controller`, the composition root
in `create_app`'s lifespan, and the pytest-bdd steps in `tests/apps/cms_backend/conftest.py`.

Behavior is ported from `reference/daily-trends-node/src/contexts/cms/shared/domain/Criteria.ts`,
`.../feeds/application/search/FeedSearcher.ts`, `.../shared/infrastructure/persistence/mongo/MongoRepository.ts`
(`byCriteria`), `.../feeds/infrastructure/persistence/mongo/MongoFeedRepository.ts` (`search`),
`.../apps/cms/backend/controllers/feeds/FeedListController.ts`, `list-feed.feature` and the `search`
tests in `MongoFeedRepository.test.ts`.

### Agreed decisions

- **Granularity:** minimum, 1 phase.
- **Criteria** is a `TypedDict(total=False)` mirroring the reference interface: an absent key means
  no filter, no sort or no limit. `None` or `{}` returns every feed.
- **Use case** is `FeedSearcher` under `application/search`, as in the reference, so S07 reuses it.

### Smaller decisions

- **No `$or` without a filter.** Node sends `{ $or: undefined }`, which its driver drops because of
  `ignoreUndefined`. Mongo rejects an empty `$or`, so the port leaves out `$or` when `filter` is absent
  or empty. Same observable behavior.
- **Sort** maps `asc` → `1` and `desc` → `-1`. Ordering stays textual over the stored ISO strings.
  Ties keep Mongo's natural order (unspecified, as in Node).
- **Limit** `0` or absent means no limit (Mongo's `limit(0)`).
- **Errors:** `GET /feed/list` takes no input, so it maps no domain error; anything raised answers
  500 `{"error": …}` through `run_controller`, as the Node base controller does.
- **In-memory fake:** `InMemoryFeedRepository.search` records the criteria it receives and returns the
  stored feeds without evaluating the criteria. Criteria semantics are covered by the Mongo
  integration tests.

## Phases

## Phase 1: List feeds end to end

Add `Criteria`, the criteria search in the Mongo base repository, `FeedRepository.search`,
`FeedSearcher`, and `GET /feed/list`.

### Public contracts

- `daily_trends_py.contexts.cms.shared.domain.criteria`:
  - `type SortDirection = Literal["asc", "desc"]`
  - `class Criteria(TypedDict, total=False)`: `filter: list[Mapping[str, object]]` (conditions combined
    with OR, each a field → value equality map), `sort: Mapping[str, SortDirection]`, `limit: int`.
- `FeedRepository` Protocol gains `async search(criteria: Criteria | None = None) -> list[Feed]`.
- `MongoRepository._by_criteria(criteria: Criteria) -> list[MongoDocument]`: query `{"$or": filter}`
  only when `filter` is non-empty, sort as given (`asc` → 1, `desc` → -1), `limit` or `0`; each
  document maps `_id` to `id` as `_by_id` does.
  *(Implementation: `_by_id` and `_by_criteria` share a module-level `_with_id` helper.)*
- `MongoFeedRepository.search(criteria=None)` maps every document with `Feed.from_primitives`.
- `daily_trends_py.contexts.cms.feeds.application.search.feed_searcher.FeedSearcher(repository)`:
  `async execute(criteria: Criteria | None = None) -> list[Feed]`.
- Composition root: `FeedSearcher` built in the lifespan and kept on `app.state.feed_searcher`.
- HTTP: `GET /feed/list` → 200 with `[feed.to_primitives(), …]` from
  `execute({"sort": {"createdAt": "desc"}})`; no feeds → `[]`. Registered before `GET /feed/{id}`.
- Test suites:
  - `tests/apps/cms_backend/features/list-feed.feature` (verbatim from the reference) and
    `tests/apps/cms_backend/test_list_feeds.py`. The `There are feeds:` step uses the `createdAt`
    column when present and not empty, and a random date otherwise.
    *(Implementation: `The response should contains:` now compares nested shapes. A list must have
    the same length and order, and each element only its listed keys, so the feature checks the
    order without the random `updatedAt`.)*
  - `tests/contexts/cms/feeds/application/search/test_feed_searcher.py`.
  - `InMemoryFeedRepository.search` plus a `searched_criteria: list[Criteria | None]` record.
  - `search` tests in `tests/contexts/cms/feeds/infrastructure/persistence/mongo/test_mongo_feed_repository.py`
    (marked `integration`).

### Tests first

- [x] `FeedSearcher` returns the feeds from the repository and passes the criteria through unchanged (in-memory fake).
- [x] `integration`: `search()` with no criteria returns every stored feed; on an empty collection it returns `[]`.
- [x] `integration`: with 3 CMS, 1 EL_PAIS and 1 EL_MUNDO feeds, `filter: [{"source": "CMS"}]` returns the 3 CMS feeds; `filter: [{"source": "EL_PAIS"}, {"source": "EL_MUNDO"}]` returns 2 (OR).
- [x] `integration`: `sort: {"createdAt": "desc"}` returns feeds newest first; `"asc"` oldest first.
- [x] `integration`: `limit: 2` with a descending sort returns the 2 newest; `limit: 0` returns all.
- [x] `integration`: `list-feed.feature` — five feeds → 200 ordered by `createdAt` descending; no feeds → 200 `[]`.

### Implementation

- [x] Add `criteria.py` to the shared domain.
- [x] Add `_by_criteria` to `MongoRepository` and `search` to `FeedRepository` and `MongoFeedRepository`.
- [x] Add `FeedSearcher` and the in-memory fake's `search`.
- [x] Add `GET /feed/list` in `routes/feed.py` before `/feed/{id}` and wire `FeedSearcher` in `create_app`'s lifespan.
- [x] Extend the `There are feeds:` step to read an optional `createdAt` column.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Next step

Phase 1 is implemented and awaits review (and an optional `/ai-project-conventional-commit`).
Then push the branch, open a PR, and plan S04 with
`/ai-project-create-plan specs/feeds/S04-update-feed.md`.
