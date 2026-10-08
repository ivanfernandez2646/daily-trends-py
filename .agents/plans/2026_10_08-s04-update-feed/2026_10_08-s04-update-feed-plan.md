---
name: 's04-update-feed'
description: 'PATCH /feed/{id} updates title and description, saving only when something changes'
spec: 'specs/feeds/S04-update-feed.md'
branch: 'feat/s04-update-feed'
created_at: '2026-10-08T09:53:44Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
implemented_at: '2026-10-08T10:05:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S04 · Update a feed

## Goal

Update a feed's `title` and `description` with `PATCH /feed/{id}`, with the same status codes and
bodies as the Node reference. Absent or falsy titles are ignored, and an update that changes nothing
neither saves nor touches `updatedAt`. No event is emitted. The repository stays green.

## Context

S02 delivered the `Feed` aggregate, the value objects with `from_raw` (raw input → value object or
`InvalidArgumentError`), `MISSING`, `find_feed` (raises `FeedNotFound`), `parse_body`,
`run_controller`, and the pytest-bdd steps in `tests/apps/cms_backend/conftest.py`. S03 added
`FeedSearcher`. `MongoRepository._persist` already upserts with `$set`, so `save` covers updates.

Behavior is ported from `reference/daily-trends-node/src/contexts/cms/feeds/domain/Feed.ts` (`update`,
`equalsTo`), `.../feeds/application/update/FeedUpdater.ts`,
`.../apps/cms/backend/controllers/feeds/FeedUpdaterController.ts`, `update-feed.feature` and
`FeedUpdater.test.ts`.

### Agreed decisions

- **Granularity:** minimum, 1 phase.
- **Non-string values follow S02's deliberate divergence.** A truthy non-string `title` (e.g. `5`,
  `[]`, `{}`, `true`) → 400 `<FeedTitle> is mandatory. Current value: <…>`. A non-string `description`
  → 400 `<FeedDescription> does not allow the value <…>`. Node answered 500 or stored the value as it
  came. Both reuse the existing `from_raw`.

### Smaller decisions

- **Falsy title uses JavaScript falsiness, not Python's.** The title is ignored when it is `MISSING`,
  `None`, `""`, `False` or numeric zero. An empty list or object counts as truthy, so it gives a 400 as
  above. This lives in the use case (`_is_falsy`) so the use-case tests cover it.
- **Description:** `MISSING` → unchanged; any other value (including `None` and `""`) →
  `FeedDescription.from_raw`.
- **Validation order follows the reference:** id (400) → find (404) → title (400) → description (400).
  So a missing feed with an invalid title answers 404.
- **`Feed.update` returns a new `Feed`, or `None` when nothing changes**, as in the reference. Equality
  compares `title` and `description`, the only fields `update` can change. A new feed gets
  `updated_at = DateTimeValueObject.now()` and records no event.
- **Any source** can be updated: there is no source check.

## Phases

## Phase 1: Update a feed end to end

Add `Feed.update`, the `FeedUpdater` use case, and `PATCH /feed/{id}`.

### Public contracts

- `Feed.update(*, title: FeedTitle | None = None, description: FeedDescription | None = None) -> Feed | None`:
  `None` argument → keep the current value; `FeedDescription(None)` sets the description to `null`.
  Returns `None` when the result equals the current feed; otherwise a new `Feed` with the same `id`,
  `author`, `source`, `created_at`, and `updated_at` = now.
- `daily_trends_py.contexts.cms.feeds.application.update.feed_updater`:
  - `class FeedUpdaterProps(TypedDict)`: `id: object`, `title: object`, `description: object` (raw
    input, `MISSING` when not sent, as in `FeedCreatorProps`).
  - `FeedUpdater(repository: FeedRepository)`: `async execute(props: FeedUpdaterProps) -> Feed`.
    Returns the current feed unchanged when there is nothing to update (no save), or saves and returns
    the updated feed.
- Composition root: `FeedUpdater` built in the lifespan and kept on `app.state.feed_updater`.
- HTTP: `PATCH /feed/{id}` with a JSON or urlencoded body (`parse_body`) → 200 `feed.to_primitives()`;
  `FeedNotFound` → 404 `{"error": "Feed with id <…> not found"}`; `InvalidArgumentError` → 400
  `{"error": …}`; anything else → 500 through `run_controller`.
- Test suites:
  - `tests/apps/cms_backend/features/update-feed.feature` (verbatim from the reference) and
    `tests/apps/cms_backend/test_update_feed.py` (marked `integration`).
  - New step `I send a PATCH request to "{path}" with body:` in `tests/apps/cms_backend/conftest.py`.
  - `tests/contexts/cms/feeds/application/update/test_feed_updater.py`.
  - `Feed.update` tests in `tests/contexts/cms/feeds/domain/test_feed.py`.

### Tests first

- [x] `Feed.update` with no arguments, or with the current title and description, returns `None`.
- [x] `Feed.update` with a new title returns a feed with that title, the same other fields, and a new `updated_at`; it records no domain event.
- [x] `Feed.update(description=FeedDescription(None))` on a feed with a description returns a feed whose description is `None`.
- [x] `FeedUpdater` raises `FeedNotFound` when the feed does not exist and saves nothing.
- [x] `FeedUpdater` with every field `MISSING` (PATCH `{}`) returns the stored feed and saves nothing.
- [x] `FeedUpdater` with the same title and description returns the stored feed, saves nothing, and keeps `updated_at`.
- [x] `FeedUpdater` with a new title and description saves and returns the updated feed with a non-null `updated_at`.
- [x] `FeedUpdater` ignores a falsy title (`""`, `None`, `False`, `0`) and saves nothing when nothing else changes.
- [x] `FeedUpdater` with `title: "   "` raises `InvalidArgumentError` `<FeedTitle> is mandatory. Current value: <   >`; with `title: []` it raises the same error with `<>`.
- [x] `FeedUpdater` with a non-string `description` raises `InvalidArgumentError` `<FeedDescription> does not allow the value <…>`.
- [x] `FeedUpdater` with `description: None` or `""` on a feed with a description saves the new value.
- [x] `FeedUpdater` with an invalid id raises `InvalidArgumentError`; with a missing feed and an invalid title it raises `FeedNotFound`.
- [x] `integration`: `update-feed.feature` — missing feed → 404 with the error body; existing feed → 200 with the new title and the other fields unchanged.
- [x] `integration`: PATCH `{}` → 200 with the unchanged feed, `updatedAt` included.
- [x] `integration`: PATCH `description: null` → 200 with `description: null` and a changed `updatedAt`, and a following GET returns the same feed.
- [x] `integration`: PATCH `title: "  "` → 400 `{"error": "<FeedTitle> is mandatory. Current value: <  >"}`; PATCH on `/feed/not-a-uuid` → 400.

### Implementation

- [x] Add `Feed.update`.
- [x] Add `FeedUpdater` and `FeedUpdaterProps` under `application/update`.
- [x] Add `PATCH /feed/{id}` in `routes/feed.py` and wire `FeedUpdater` in `create_app`'s lifespan.
- [x] Add the PATCH step and copy `update-feed.feature`.
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
Then push the branch, open a PR, and plan S05 with
`/ai-project-create-plan specs/feeds/S05-delete-feed.md`.
