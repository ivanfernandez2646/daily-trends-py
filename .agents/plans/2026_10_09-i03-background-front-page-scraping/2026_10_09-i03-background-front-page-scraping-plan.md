---
name: 'i03-background-front-page-scraping'
description: 'Scraping runs one at a time, /feed/home refreshes a stale page in the background instead of inside the request, and background runs respect a 5-minute cooldown'
spec: 'specs/improvements/I03-background-front-page-scraping.md'
branch: 'fix/i03-background-front-page-scraping'
created_at: '2026-10-09T12:38:30Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
implemented_at: '2026-10-09T12:51:18Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I03 · Background front-page scraping

## Goal

Resolve improvements #17, #5 and #4. Scraping runs never overlap in the process. `/feed/home`
answers at once and refreshes a stale page with a background task kept in a strong reference, which
is cancelled on shutdown. A background run does not start within 5 minutes of the previous one's
end. The repository stays green after each phase.

## Context

- Branch `fix/i03-background-front-page-scraping` is cut from `main`, which already contains I01
  and I02.
- `application/scrap/feed_scraper.py`: `FeedScraper.execute()` gathers every `FeedScrap`, drops
  failing ones with a logged warning, deduplicates by `(source, title, UTC day)` against the
  repository (`exists_headline`) and within the run, saves and returns the saved feeds. It has no
  concurrency guard.
- `application/home/feed_home_searcher.py`: `FeedHomeSearcher(repository, scraper, clock)`
  searches `HOME_CRITERIA`. When the newest feed is from an earlier local day, it awaits
  `scraper.execute()` and searches again.
- `apps/cms_backend/main.py` builds everything in `lifespan`: one `FeedScraper` shared by
  `/feed/scrap` (`app.state.feed_scraper`) and `FeedHomeSearcher`. On exit it closes the httpx client
  and then Mongo. Constants `SCRAP_TIMEOUT_SECONDS` and `SCRAP_USER_AGENT` live there.
- `Clock` port (`now()`, aware, local zone); `SystemClock`; test fake `FixedClock(now)`.
- Fakes: `StubFeedScrap(feeds, error)` counts `calls`; `InMemoryFeedRepository`,
  `FailingFeedRepository`.
- App tests (`integration`): `tests/apps/cms_backend/test_home_feeds.py` and `test_scrap_feeds.py`
  with `FrontPagesTransport` fixtures. `run_in_app(client, fn)` runs a coroutine on the app loop.
- The app runs as a single uvicorn process, so an in-process guard is enough (spec edge case).
- `specs/feeds/S07-front-page.md` gets "Superseded by I03" notes next to each rule a phase changes.

## Phase 1: Single-flight scraping (#17)

Scraping runs are serialized in `FeedScraper`, so a second run waits and then deduplicates against
the first. No HTTP contract changes.

### Public contracts

- `FeedScraper.execute() -> list[Feed]`: holds an internal `asyncio.Lock` for the whole run. A
  concurrent call waits for the run in progress, then performs its own run.
- `FeedScraper.is_running -> bool` (property): `True` while a run holds the lock.
- Test fake `BlockingFeedScrap(feeds)`: `scrap()` records the call and waits until `release()` is
  called. `started` is an `asyncio.Event` set on the first call.

### Tests first

- [x] `test_feed_scraper.py`: two concurrent `execute()` calls with the same headlines. The second
      does not call the scrapers until the first finishes, and returns `[]`. The headlines are saved
      once.
- [x] `test_feed_scraper.py`: `is_running` is `False` before a run, `True` while a scraper is
      blocked, and `False` after the run, including after a run whose save raised.

### Implementation

- [x] Add `BlockingFeedScrap` to `tests/contexts/cms/feeds/fakes/`.
- [x] Add the lock and `is_running` to `FeedScraper`.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggested commits:
  - `fix(i03): run one feed scraping at a time`
  - `fix(i03): serialize concurrent scraping runs so headlines are not stored twice`
  - `test(i03): cover concurrent scraping runs with a blocking scraper fake`

## Phase 2: Background refresh on `/feed/home` (#5)

`/feed/home` no longer waits for scraping. A stale page requests one background run. Its errors are
logged, it is kept in a strong reference, and shutdown cancels it. There is no cooldown yet.

### Public contracts

- New `application/home/feed_home_refresher.py`:
  - `FeedHomeRefresher(scraper: FeedScraper, clock: Clock, cooldown: timedelta)`. The cooldown is
    accepted but only enforced in Phase 3.
  - `request() -> None`: synchronous and non-blocking. It is ignored while its own task is alive or
    while `scraper.is_running`. Otherwise it starts `scraper.execute()` with
    `asyncio.create_task` and keeps the task in `self._task` until it finishes. An exception from
    the run is logged with `logger.exception` and never propagates.
  - `async join() -> None`: awaits the run in progress, if any. Used by tests and never raises the
    run's error.
  - `async aclose() -> None`: cancels the run in progress and awaits it.
- `FeedHomeSearcher(repository, refresher: FeedHomeRefresher, clock)`: `execute()` searches once.
  When the page is stale it calls `refresher.request()` and returns the first search's feeds.
- `main.py`: `SCRAP_COOLDOWN = timedelta(minutes=5)`, `app.state.feed_home_refresher`. `lifespan`
  awaits `refresher.aclose()` before closing the httpx and Mongo clients.
- `GET /feed/home`: a stale page answers 200 with the stale feeds. A save error during the
  background run is logged, not answered as 500.
- `docs/openapi.yml`: `/feed/home` says a stale page triggers a background refresh and may be
  returned stale; `/feed/scrap` says it waits for a run in progress.

### Tests first

- [x] `test_feed_home_refresher.py`:
  - `request()` starts one scraper run and returns before it finishes;
  - a second `request()` while the run is blocked is ignored (one scraper call);
  - `request()` while a manual `scraper.execute()` is in progress is ignored;
  - a run whose save raises is logged (`caplog`), `join()` does not raise, and a later `request()`
    starts a new run;
  - `aclose()` cancels a blocked run, and nothing is saved after the cancellation;
  - the task stays referenced while running and is released after it finishes. (Tested through
    behavior: a request is ignored while the task is alive, and a new one starts after it finishes.
    No test inspects the private attribute.)
- [x] `test_feed_home_searcher.py`: rewrite for the refresher:
  - a stale page returns the first search, with one search only, and requests a run;
  - fresh or empty pages request nothing;
  - the local-day parametrized test stays;
  - a failing scrap no longer propagates. This replaces `test_propagates_a_save_error_...` and the
    "retries on every call" test, which Phase 3 covers.
- [x] `test_home_feeds.py` (integration): a stale `/feed/home` answers 200 with the stale feed. After
      `run_in_app(client, refresher.join)`, `/feed/list` has 11 feeds and `/feed/home` returns the
      10 scraped ones. When every source fails, it keeps answering the stale feed.
- [x] `test_scrap_feeds.py` (integration): `/feed/scrap` still answers the saved feeds after a
      background run has finished (same-day duplicates give `[]`).
- [x] `home-feed.feature` passes unchanged.

### Implementation

- [x] Add `FeedHomeRefresher` and switch `FeedHomeSearcher` to it.
- [x] Wire it in `main.py` and close it in `lifespan` before the clients. (The cancellation is
      unit-tested through `aclose()`. The shutdown order in `lifespan` has no app-level test,
      because the mock transport makes a hanging run impractical to observe.)
- [x] `docs/openapi.yml`. Add S07 "Superseded by I03" notes on inline scraping, the re-search and
      the 500 on a scraping error.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggested commits:
  - `fix(i03): scrape a stale front page in the background`
  - `fix(i03): answer /feed/home without waiting for scraping`
  - `feat(i03): add a background front page refresher cancelled on shutdown`

## Phase 3: Cooldown between background runs (#4)

A background refresh does not start within 5 minutes of the previous background run's end,
whatever its outcome. Manual runs ignore the cooldown and never start it.

### Public contracts

- `FeedHomeRefresher.request()`: also ignored when the last background run finished less than
  `cooldown` ago according to `clock.now()`. The end time is recorded in the task's `finally`, so it
  is set after success, an empty run or an error. A cancelled run does not record it.
- `FixedClock.advance(delta: timedelta) -> None` (test fake).

### Tests first

- [ ] `test_feed_home_refresher.py`:
  - after a run ends, a `request()` at `cooldown - 1 µs` is ignored and one at exactly `cooldown`
    starts a run, after both a successful and a failing run;
  - a manual `scraper.execute()` neither starts the cooldown nor is blocked by it.
- [ ] `test_feed_home_searcher.py` or `test_home_feeds.py`: when every source fails, repeated stale
      requests within 5 minutes start one run.

### Implementation

- [ ] Add `FixedClock.advance`.
- [ ] Record the last background run's end time and check it in `request()`.
- [ ] S07 "Superseded by I03" note on the "retry on every request" edge case.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Review Phase 2, then run `/ai-project-implement-phase .agents/plans/2026_10_09-i03-background-front-page-scraping/2026_10_09-i03-background-front-page-scraping-plan.md`
to implement Phase 3.
