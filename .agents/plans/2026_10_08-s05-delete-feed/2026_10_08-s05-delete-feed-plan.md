---
name: 's05-delete-feed'
description: 'DELETE /feed/{id} removes a feed of any source, answering 404 when it does not exist'
spec: 'specs/feeds/S05-delete-feed.md'
branch: 'feat/s05-delete-feed'
created_at: '2026-10-08T09:59:34Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
implemented_at: '2026-10-08T10:01:13Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S05 · Delete a feed

## Goal

Delete a feed with `DELETE /feed/{id}`, with the same status codes and bodies as the Node reference:
404 with the error body when the feed is missing, otherwise 200 with an empty body. Any source can be
deleted and no event is emitted. The repository stays green.

## Context

S02 delivered `FeedId`, `find_feed` (raises `FeedNotFound`), `run_controller`, and the pytest-bdd steps
in `tests/apps/cms_backend/conftest.py`. S01 delivered `MongoRepository._remove`, which already has
tests for deleting a document and ignoring a missing one. The `FeedRepository` port has no `delete`
yet.

Behavior is ported from `reference/daily-trends-node/src/contexts/cms/feeds/application/delete/FeedDeleter.ts`,
`.../apps/cms/backend/controllers/feeds/FeedDeleterController.ts`, `.../infrastructure/persistence/mongo/MongoFeedRepository.ts`
(`delete`), `delete-feed.feature`, and `FeedDeleter.test.ts`.

### Agreed decisions

- **Granularity:** minimum, 1 phase.
- **No `Feed.delete()`.** The reference method is an empty TODO for a future `feed.deleted` event.
  Porting it would add a method that does nothing.
- **`FeedRepository.delete` takes a `Feed`**, as in the reference.
- **`FeedDeleter.execute` takes a `FeedId`**, like `FeedFinder`. The route builds it, so an invalid id
  answers 400 through `InvalidArgumentError`.

### Smaller decisions

- **200 with an empty body** (no content type, `Content-Length: 0`). Improvement #11 (204) is out of
  scope.
- **Any source** can be deleted: there is no source check.
- **Order:** id (400) → find (404) → delete.

## Phases

## Phase 1: Delete a feed end to end

Add `delete` to the repository port and its adapters, the `FeedDeleter` use case, and
`DELETE /feed/{id}`.

### Public contracts

- `FeedRepository.delete(feed: Feed) -> None`.
  - `MongoFeedRepository.delete` removes the document with `_remove(feed.id.value)`.
  - `InMemoryFeedRepository.delete` removes the feed and records it in `deleted: list[Feed]`.
- `daily_trends_py.contexts.cms.feeds.application.delete.feed_deleter`:
  `FeedDeleter(repository: FeedRepository)`: `async execute(id: FeedId) -> None`. Raises `FeedNotFound`
  when the feed does not exist; otherwise deletes it.
- Composition root: `FeedDeleter` built in the lifespan and kept on `app.state.feed_deleter`.
- HTTP: `DELETE /feed/{id}` → 200 with an empty body; `FeedNotFound` → 404
  `{"error": "Feed with id <…> not found"}`; `InvalidArgumentError` → 400 `{"error": …}`; anything else
  → 500 through `run_controller`.
- Test suites:
  - `tests/apps/cms_backend/features/delete-feed.feature` (verbatim from the reference) and
    `tests/apps/cms_backend/test_delete_feed.py` (marked `integration`).
  - New steps `I send a DELETE request to "{path}"` and `The response should be empty` in
    `tests/apps/cms_backend/conftest.py`.
  - `tests/contexts/cms/feeds/application/delete/test_feed_deleter.py`.
  - `delete` tests in `tests/contexts/cms/feeds/infrastructure/persistence/mongo/test_mongo_feed_repository.py`.

### Tests first

- [x] `FeedDeleter` raises `FeedNotFound` when the feed does not exist and deletes nothing.
- [x] `FeedDeleter` deletes an existing feed (`repository.deleted == [feed]`).
- [x] `FeedDeleter` deletes a feed whose source is not CMS.
- [x] `integration`: `MongoFeedRepository.delete` removes the feed, so `find` returns `None`, and leaves other feeds stored.
- [x] `integration`: `delete-feed.feature`: missing feed → 404 with the error body; existing feed → 200 with an empty body.
- [x] `integration`: after a DELETE, a GET of the same id answers 404.
- [x] `integration`: DELETE on `/feed/not-a-uuid` → 400 `{"error": "<FeedId> does not allow the value <not-a-uuid>"}`.

### Implementation

- [x] Add `delete` to `FeedRepository`, `MongoFeedRepository`, and `InMemoryFeedRepository`.
- [x] Add `FeedDeleter` under `application/delete`.
- [x] Add `DELETE /feed/{id}` in `routes/feed.py` and wire `FeedDeleter` in `create_app`'s lifespan.
- [x] Add the DELETE and empty-body steps and copy `delete-feed.feature`.
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
Then push the branch, open a PR, and plan S06 with
`/ai-project-create-plan specs/feeds/S06-scrape-external-sources.md`.
