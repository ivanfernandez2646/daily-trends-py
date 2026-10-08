---
name: 'i01-http-contract-fixes'
description: 'Duplicate feed answers 409, DELETE answers 204, /feed/scrap returns the saved feeds, PATCH validates a present title like PUT, date-time errors name their value object and invalid stored data answers 500'
spec: 'specs/improvements/I01-http-contract-fixes.md'
branch: 'fix/i01-http-contract-fixes'
created_at: '2026-10-08T11:09:26Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
implemented_at: '2026-10-08T11:32:21Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I01 · HTTP contract fixes

## Goal

Resolve improvements #2, #7, #11, #16 and #19 so that status codes and error messages describe
what happened. A duplicate `PUT` answers 409. A `DELETE` answers 204. `/feed/scrap` returns the
feeds it saved. `PATCH` validates a title that is present exactly as `PUT` does. Date-time errors
name `FeedCreatedAt`/`FeedUpdatedAt`. A stored document that a value object rejects answers 500 on
every route, never 400. The repository stays green after each phase.

## Context

- The port (S00–S07) is complete. This is the first improvement spec; `AGENTS.md` now allows
  `specs/improvements/I0N-*.md` specs to supersede `S0N` behavior.
- Status mapping lives in `src/daily_trends_py/apps/cms_backend/routes/feed.py` through
  `run_controller` (`apps/cms_backend/controllers.py`): each route maps only the errors it declares,
  everything else is `500 {"error": str(error)}`.
- Acceptance tests are pytest-bdd scenarios in `tests/apps/cms_backend/features/*.feature` with
  extra cases in `tests/apps/cms_backend/test_*.py`, run against real Mongo (`integration` marker).
- `FeedScraper.execute()` returns `None` and keeps the id-regeneration loop (#6, out of scope).
- `FeedUpdater` skips any "falsy" title (`MISSING`, `None`, `""`, `0`) through `_is_falsy`.
- `DateTimeValueObject` raises `<Function> doesn't allow the value <{value}>`; `Feed` types its dates
  with the generic `RequiredDateTimeValueObject` and `DateTimeValueObject`.
- `MongoFeedRepository.find`/`search` call `Feed.from_primitives`, whose value objects raise
  `InvalidArgumentError` (mapped to 400 by `/feed/:id` routes and `/feed/home`).
- `docs/openapi.yml` documents `302` for `PUT` and `200` for `DELETE` and `/feed/scrap`.
- The `S0N` specs stay as the record of ported behavior. Each phase adds a one-line
  "Superseded by I01" note next to the sections it changes.

## Phase 1: Duplicate feed → 409, DELETE → 204

The two changes that only touch status codes in the routes.

### Public contracts

- `PUT /feed/:id` with an existing id → `409 {"error": "Feed with id <{id}> already exists"}`.
- `DELETE /feed/:id` on an existing feed → `204`, empty body.
- `docs/openapi.yml`: `PUT` documents `409` instead of `302`; `DELETE` documents `204` instead of `200`.

### Tests first

- [x] `features/create-feed.feature`: the duplicate scenario expects status `409`.
- [x] `test_create_feed.py`: rename the 302 test to `..._answers_409_and_keeps_the_first_feed` and
      assert `409`.
- [x] `features/delete-feed.feature`: the existing-feed scenario expects `204` and an empty body.
- [x] `test_delete_feed.py`: `test_a_deleted_feed_is_no_longer_found` asserts `204`.
- [x] `test_controllers.py`: the already-exists mapping test uses `409` (keep the "no `Location`"
      assertion).

### Implementation

- [x] `routes/feed.py`: map `FeedAlreadyExists` to `HTTP_409_CONFLICT`; `delete_feed` returns
      `Response(status_code=HTTP_204_NO_CONTENT)`.
- [x] Update `docs/openapi.yml`.
- [x] Add "Superseded by I01" notes in S01 (error table), S02 (create), S05.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: `/feed/scrap` returns the saved feeds

### Public contracts

- `FeedScraper.execute(self) -> list[Feed]`: the feeds saved by this run, in scraper order then
  article order, with the id they were saved under.
- `GET /feed/scrap` → `200` with a JSON array of `Feed.to_primitives()`; `[]` when nothing is saved.
- `FeedHomeSearcher` keeps calling `execute()` and ignores the result.
- `docs/openapi.yml`: `/feed/scrap` `200` documents an array of feeds.

### Tests first

- [x] `test_feed_scraper.py`: returns the saved feeds in scraper order; when one scraper fails it
      returns only the other's feeds; returns `[]` when every scraper fails; a regenerated id is the
      one in the returned feed.
- [x] `features/scrap-feed.feature`: the `/feed/scrap` step expects `The response is an array with
      length 10` instead of an empty body.
- [x] `test_scrap_feeds.py`: one source failing → the response is 5 `EL_ESPANOL` feeds equal to
      `/feed/list`; every source failing → `200` with `[]`.

### Implementation

- [x] `FeedScraper.execute` collects and returns the saved feeds.
- [x] `routes/feed.py`: `scrap_feeds` returns `JSONResponse([...to_primitives()], 200)`.
- [x] Update `docs/openapi.yml`; add a "Superseded by I01" note in S06.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 3: `PATCH` validates a present title like `PUT`

### Public contracts

- `FeedUpdater.execute`: `title` `MISSING` → unchanged; any other value → `FeedTitle.from_raw`
  (non-string or blank → `InvalidArgumentError("<FeedTitle> is mandatory. Current value: <{value}>")`).
  `description` rule unchanged. Order unchanged: id → find (404) → title → description.
- `PATCH /feed/:id` → 400 for `title` `""`, `"  "`, `null`, `0`.

### Tests first

- [x] `test_feed_updater.py`: parametrized `""`, `None`, `0` titles raise `InvalidArgumentError`
      with the exact message and save nothing; an absent title keeps the stored one.
- [x] `test_update_feed.py`: `{"title": ""}` → `400 <FeedTitle> is mandatory. Current value: <>`;
      `{"title": null}` → `400 ... <null>`; `{"title": ""}` on a missing feed → `404`.

### Implementation

- [x] `FeedUpdater`: replace `_is_falsy` with a `MISSING` check and delete the helper.
- [x] Add a "Superseded by I01" note in S04 (absence rule).
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 4: Date-time errors name the value object; invalid stored data → 500

#16 lands first in this phase because #19's 500 body carries the value object's message.

### Public contracts

- `DateTimeValueObject` and `RequiredDateTimeValueObject` raise
  `InvalidArgumentError("<{ClassName}> does not allow the value <{value}>")`.
- New `FeedCreatedAt(RequiredDateTimeValueObject)` and `FeedUpdatedAt(DateTimeValueObject)` in
  `contexts/cms/feeds/domain/`. `Feed.created_at: FeedCreatedAt`, `Feed.updated_at: FeedUpdatedAt`;
  `Feed.create`, `Feed.update` and `Feed.from_primitives` build them.
- New `InvalidStoredFeed(Exception)` in
  `contexts/cms/feeds/infrastructure/persistence/mongo/invalid_stored_feed.py`, message
  `Stored feed <{id}> is invalid: {reason}`. `MongoFeedRepository.find` and `search` raise it when
  `Feed.from_primitives` raises `InvalidArgumentError`. No route maps it, so it answers 500.
- `routes/feed.py`: `/feed/home` maps no error to 400.
- `docs/openapi.yml`: document `500` for invalid stored data on the feed routes.

### Tests first

- [x] `test_date_time_value_object.py`: messages name the class and say "does not allow".
- [x] `test_feed_value_objects.py`: `FeedCreatedAt("not-a-date")` →
      `<FeedCreatedAt> does not allow the value <not-a-date>`; same for `FeedUpdatedAt`.
- [x] Add `FeedCreatedAtMother` and `FeedUpdatedAtMother`; `FeedMother` and the acceptance tests use
      them instead of the generic date-time mothers; the generic date-time mothers are removed
      as unused.
- [x] `test_mongo_feed_repository.py`: a raw document with `createdAt: "not-a-date"` makes `find`
      and `search` raise `InvalidStoredFeed` with the full message.
- [x] Acceptance (one parametrized `test_invalid_stored_feed.py` instead of one test per route file,
      since the scenario is identical): a raw malformed document inserted into Mongo makes
      `GET /feed/:id`, `PUT /feed/:id`, `PATCH /feed/:id`, `DELETE /feed/:id`, `GET /feed/list` and
      `GET /feed/home` answer `500 {"error": "Stored feed <{id}> is invalid: <FeedCreatedAt> does not
      allow the value <not-a-date>"}`.
- [x] An invalid UUID in the path still answers 400 (existing tests stay green).

### Implementation

- [x] Pass the class name into the date-time parse check; drop the `<Function>` comment.
- [x] Add `FeedCreatedAt`/`FeedUpdatedAt` and retype `Feed`.
- [x] Add `InvalidStoredFeed` and wrap reconstruction in `MongoFeedRepository`.
- [x] Remove the `InvalidArgumentError` mapping from `home_feeds`.
- [x] Update `docs/openapi.yml`; add "Superseded by I01" notes in S02 (date-time row), S03 and S07.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Next step

All phases are implemented. After reviewing Phase 4, commit it and open a pull request for `fix/i01-http-contract-fixes`.
