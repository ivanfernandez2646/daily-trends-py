---
name: 's07-front-page'
description: 'GET /feed/home returns the 10 newest external feeds and scrapes inline when the newest is from a previous day'
spec: 'specs/feeds/S07-front-page.md'
branch: 'feat/s07-front-page'
created_at: '2026-10-08T10:37:46Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
implemented_at: '2026-10-08T10:40:26Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S07 · Front page

## Goal

`GET /feed/home` returns up to 10 feeds from `EL_MUNDO` and `EL_ESPANOL`, newest first.
When there are results and the newest one is from a day before today (server local time), it runs
the S06 scraping inside the request and searches again. With no results it does not scrape and
returns `[]`. The behavior and its defects match the Node reference. El Español replaces El País
in the filter because it replaces it as a scraped source and the database starts empty. The repository stays green after each
phase.

## Context

S03 delivered `Criteria` (an OR list of field → value conditions, plus `sort` and `limit`),
`FeedRepository.search` and the Mongo text ordering over ISO `createdAt` strings. S06 delivered
`FeedScraper(repository, scrapers)`. It drops a scraper that fails, propagates a save error, and is
wired in `create_app` with both scrapers. `FrontPagesTransport` serves 5 + 5 fixture feeds. The
`routes/__init__.py` docstring already says static `/feed/*` routes go above `/feed/{id}`.
`scrap-feed.feature` notes that its `/feed/home` checks return with S07.

Behavior is ported from the following files under `reference/daily-trends-node/`:

- `src/apps/cms/backend/controllers/feeds/FeedHomeController.ts` (the reference keeps the logic in
  the controller)
- `src/apps/cms/backend/routes/feed.route.ts` and `dependency-injection/apps/feed.yaml`
- `tests/apps/cms/backend/controllers/feeds/home-feed.feature` and `scrap-feed.feature`
- `tests/apps/cms/backend/shared/FeedRepository.ts` (the `There are feeds:` step)

### Findings

- **The reference day check** is `moment(feeds[0].createdAt.value).isBefore(moment(), 'date')`. It
  compares calendar days, both in the server's local zone. `feeds[0]` is the first item of the
  result, sorted by `createdAt` descending.
- **The reference harness treats an empty or missing `createdAt` as now.** That is why "Test Feed
  Find 4" is first in `home-feed.feature` and why that scenario does not scrape. Our
  `There are feeds:` step uses a random date instead, so `home-feed.feature` would be
  nondeterministic. S07 said the order came from text ordering of an empty value, which
  `RequiredDateTimeValueObject` would reject anyway. The spec is reworded.
- **There is no `Clock` yet.** Time comes from `datetime.now(UTC)` inside `DateTimeValueObject.now()`.
- **`InMemoryFeedRepository.search` ignores criteria.** Unit tests check `searched_criteria`, and
  seed feeds in the order a descending search would return them.
- **Out of scope:**
  - Improvement #4: the retry repeats on every request while scrapers fail.
  - Improvement #5: scraping runs inline in the request.
  - Improvement #12: dates are ordered as text.

### Agreed decisions

- **Granularity:** intermediate, 2 phases.
- **Placement:** an application use case, `FeedHomeSearcher`. The route only calls it. This differs
  from the reference controller, but the behavior is the same.
- **Spec and harness:** S07 is reworded (done while planning). The `There are feeds:` step creates a
  feed with an empty or missing `createdAt` with the current time, as the reference does. Only
  `list-feed.feature` sets `createdAt`, and it always fills it in.

- **No `EL_PAIS` on the front page** (decided after Phase 1). The database starts empty, so
  the filter is `EL_MUNDO` or `EL_ESPANOL`. `FeedSource.EL_PAIS` stays for the other routes and
  `list-feed.feature`.

### Smaller decisions

- **`Clock` port** in the shared kernel. `now()` returns an aware `datetime` in the server's local
  zone. `SystemClock` returns `datetime.now(UTC).astimezone()`.
- **Day comparison:** `datetime.fromisoformat(newest.created_at.value).astimezone(now.tzinfo).date() <
  now.date()`.
  - A stored value without an offset is read as local time, as moment does.
  - Taking the zone from the clock keeps tests deterministic whatever the machine's zone.
- **Criteria:** a module constant `HOME_CRITERIA`. Its filter, in this order, is
  `[{"source": EL_MUNDO}, {"source": EL_ESPANOL}]`, with
  `sort {"createdAt": "desc"}` and `limit 10`. The same criteria is used for the re-search.
- **No clock seam in `create_app`.** Acceptance tests use 2023 rows (stale) or "now" rows (fresh),
  so `SystemClock()` is always wired. `FixedClock` is for unit tests only.
- **Errors:** `run_controller` maps only `InvalidArgumentError` to 400. Any other error, such as a
  save error from scraping, gives 500 `{"error": …}`.

## Phases

## Phase 1: Front page search end to end

Add `FeedHomeSearcher` without scraping, `GET /feed/home`, the harness change, and
`home-feed.feature` from the reference, with its `EL_PAIS` row changed to `EL_ESPANOL`. Both
scenarios pass here: the first one never scrapes because
its newest feed is from now.

### Public contracts

- `daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher`:
  - `HOME_CRITERIA: Criteria`, as above.
  - `FeedHomeSearcher(repository: FeedRepository)` with `async execute() -> list[Feed]`.
- Composition root: `app.state.feed_home_searcher = FeedHomeSearcher(feed_repository)`.
- HTTP: `GET /feed/home` → 200 with an array of `Feed.to_primitives()`. `InvalidArgumentError` → 400
  `{"error": …}`, and any other error → 500. It is declared in `routes/feed.py` above
  `GET /feed/{id}`.
- Test support:
  - `RequiredDateTimeValueObjectMother.now()`.
  - The `There are feeds:` step uses it when `createdAt` is empty or missing.
- Test suites:
  - `tests/contexts/cms/feeds/application/home/test_feed_home_searcher.py`
  - `tests/apps/cms_backend/features/home-feed.feature` (from the reference; the `EL_PAIS` row is `EL_ESPANOL`)
  - `tests/apps/cms_backend/test_home_feeds.py` (`scenarios(...)`, marked `integration`)

### Tests first

- [x] `FeedHomeSearcher` searches once with `HOME_CRITERIA` and returns the repository's feeds.
- [x] `FeedHomeSearcher` returns `[]` when the repository has no feeds.
- [x] `integration`: `home-feed.feature`.
  - With external feeds, the response contains Feed 4 (`EL_MUNDO`, created now), then Feed 1
    (`EL_ESPANOL`), and no CMS feeds.
  - With no feeds, the response is `[]`.
- [x] `integration`: `EL_ESPANOL` feeds are included and a feed list is capped at 10 newest. Seed 11
      external feeds (including `EL_ESPANOL`) and 1 CMS feed. Give them distinct explicit
      `createdAt` values from today, so no scraping happens and no two feeds tie. Expect the 10
      newest external feeds in descending `createdAt` order.

### Implementation

- [x] Add `HOME_CRITERIA` and `FeedHomeSearcher`.
- [x] Add `RequiredDateTimeValueObjectMother.now()` and use it in the `There are feeds:` step.
- [x] Wire `feed_home_searcher` in `create_app`, then add `GET /feed/home` above `GET /feed/{id}`
      with the 400 mapping.
- [x] Add `home-feed.feature` and `test_home_feeds.py`.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms/feeds tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Phase 2: Scrape when the front page is stale

Add the `Clock` port, then make `FeedHomeSearcher` scrape and search again when the newest feed is
from a previous local day. Restore the `/feed/home` checks in `scrap-feed.feature`.

### Public contracts

- `daily_trends_py.contexts.cms.shared.domain.clock`:
  `class Clock(Protocol): def now(self) -> datetime: ...` (aware, server local zone).
- `daily_trends_py.contexts.cms.shared.infrastructure.system_clock`: `SystemClock` implements
  `Clock` with `datetime.now(UTC).astimezone()`.
- `FeedHomeSearcher(repository: FeedRepository, scraper: FeedScraper, clock: Clock)`. This changes
  the Phase 1 constructor.
- Composition root:
  `FeedHomeSearcher(feed_repository, app.state.feed_scraper, SystemClock())`. The searcher is built
  after the scraper.
- Test support: `tests/contexts/cms/shared/fakes/fixed_clock.py` with `FixedClock(now: datetime)`.
- Test suites:
  - `tests/contexts/cms/feeds/application/home/test_feed_home_searcher.py` (extended)
  - `tests/contexts/cms/shared/infrastructure/test_system_clock.py`
  - `tests/apps/cms_backend/features/scrap-feed.feature`: the reference scenario restored verbatim,
    with home=0 → list=2 → scrap → home=10 → list=12. The S07 comment is removed.
  - `tests/apps/cms_backend/test_home_feeds.py` (extended)

### Tests first

- [ ] With a `FixedClock`, the unit tests use `InMemoryFeedRepository` and a real `FeedScraper` over
      `StubFeedScrap`:
  - [ ] When the newest feed is from today, the searcher does not scrape (stub `calls == 0`) and
        searches once.
  - [ ] When the newest feed is from yesterday, the searcher scrapes once, searches twice with
        `HOME_CRITERIA`, and returns the second result, which includes the scraped feeds.
  - [ ] When there are no feeds, the searcher does not scrape and returns `[]`.
  - [ ] Only the first feed decides. A stale feed further down the list does not trigger scraping
        when the first feed is from today.
  - [ ] The comparison uses the clock's local zone, not UTC.
    - The clock is `2026-10-08T00:30+02:00` and the newest feed is `2026-10-07T22:15:00.000Z`.
      That is the same local day, so the searcher does not scrape.
    - The newest feed is `2026-10-07T21:59:00.000Z`. That is the previous local day, so it scrapes.
  - [ ] When every scraper fails, the searcher returns what already existed. Calling it again
        scrapes again (the kept defect, improvement #4).
  - [ ] A save error from scraping propagates.
- [ ] `SystemClock().now()` is timezone-aware and within a bracket of `datetime.now(UTC)`.
- [ ] `integration`: `scrap-feed.feature` restored, with home 0 → 10.
- [ ] `integration`:
  - [ ] With one stale `EL_MUNDO` feed from 2023, `GET /feed/home` scrapes through
        `FrontPagesTransport`. It answers 200 with 10 feeds, every one created today, and
        `GET /feed/list` then has 11.
  - [ ] With a stale feed and every host failing, `GET /feed/home` → 200 with just the stale feed.

### Implementation

- [ ] Add `Clock`, `SystemClock` and `FixedClock`.
- [ ] Extend `FeedHomeSearcher` with the day check, the scraping and the re-search.
- [ ] Update the wiring in `create_app`.
- [ ] Restore the `/feed/home` steps in `scrap-feed.feature`.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms tests/apps/cms_backend
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Next step

Phase 1 is implemented and awaits review (and an optional `/ai-project-conventional-commit`).
Then run `/ai-project-implement-phase` for Phase 2 on `feat/s07-front-page`.
