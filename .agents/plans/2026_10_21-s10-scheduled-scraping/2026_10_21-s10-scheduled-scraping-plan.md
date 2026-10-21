---
name: 's10-scheduled-scraping'
description: 'Every source is scraped at startup and then every 2 hours by one background scheduler; /feed/home becomes a plain read and the I03 background refresh and cooldown are removed'
spec: 'specs/feeds/S10-scheduled-scraping.md'
branch: 'feat/s10-scheduled-scraping'
created_at: '2026-10-21T09:09:30Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-21T09:40:00Z'
---

# S10 · Scheduled scraping

## Goal

A `FeedScrapeScheduler` runs the same scraping run as `/feed/scrap` as soon as the app has
started, and then one interval after each run finishes or is skipped. It shares the single-flight
guard of `FeedScraper`, never stops on errors, and is cancelled on shutdown before the clients
close. `/feed/home` only reads. The I03 refresher, staleness rule and cooldown are removed.

## Context

- `FeedScraper` (`application/scrape/feed_scraper.py`) already holds the single-flight
  `asyncio.Lock` and exposes `is_running`. A `/feed/scrap` during a scheduled run waits on that
  lock, so it needs no change.
- `FeedHomeRefresher` (`application/home/feed_home_refresher.py`) shows the existing pattern: a
  strong reference to the task, `aclose()` that cancels and awaits it, and errors logged with
  `logger.exception`. `FeedsProvider` yields it from a generator so it closes before the HTTP and
  Mongo clients. dishka closes in reverse order of creation, and the scheduler depends on
  `FeedScraper`, which depends on both clients.
- `FeedHomeSearcher` takes `refresher` and `clock` only for the staleness rule. Without that rule
  it takes only the repository.
- `IsolatedSettings` (`tests/apps/cms_backend/isolated_settings.py`) is the settings class of
  every app test, so turning the scheduler off by default there covers the whole suite.
- **Agreed:** the scheduler skips a due run when `scraper.is_running`. A run that is due in the
  event-loop step between a manual run releasing the lock and a queued `/feed/scrap` taking it
  queues behind it instead of being skipped. This is harmless: runs never overlap and dedup
  covers it, so it is not handled.
- **Agreed:** the lifespan starts the scheduler after `STARTUP_DEPENDENCIES` when
  `Settings.scrape_schedule_enabled` is true. The provider only builds and closes it.
- **Agreed:** the app `DESCRIPTION` in `main.py` still names only El Mundo and El Español
  (predates S08). It is rewritten in phase 2 to name the five sources.

## Phases

## Phase 1: The front page only reads

`/feed/home` answers the S08 selection and never starts a scraping run. `FeedHomeRefresher`, the
staleness rule and `SCRAPE_COOLDOWN_SECONDS` are removed together with their tests. After this
phase feeds only arrive through `/feed/scrap`, until phase 2.

### Public contracts

- `FeedHomeSearcher(repository: FeedRepository)` with `async execute() -> list[Feed]`, unchanged
  apart from the constructor.
- `FeedHomeRefresher` is deleted, and so is its provider in `FeedsProvider`.
- `Settings.scrape_cooldown_seconds` is removed. A leftover `SCRAPE_COOLDOWN_SECONDS` is ignored
  (`extra="ignore"`).
- OpenAPI: the `/feed/home` docstring no longer mentions a refresh.

### Tests first

- [x] `test_feed_home_searcher.py`: stale, fresh and empty pages are plain searches. Build the
      searcher with a scraper whose scrape fails the test if called, or assert through the
      constructor that no scraper can be passed. Remove the staleness and timezone tests
      (`test_returns_the_stale_feeds_at_once_and_scrapes_in_the_background`,
      `test_compares_days_in_*`, `test_returns_the_stale_feeds_when_the_background_scraping_fails`,
      `*_without_scraping_*`) and keep one test that a stale page is answered as is.
      The constructor takes only the repository, so no scraper can be called.
- [x] `test_home_feeds.py`: a stale front page is answered as is and nothing is scraped
      (`front_pages_transport.requests == []`). Remove the background-run and cooldown tests.
      The test lets the app loop run for 0.1 s before asserting. Without that, the old refresher
      had not sent its requests yet and the test passed against it.
- [x] `test_settings.py`: drop `scrape_cooldown_seconds` from the defaults and the invalid-value
      table, remove `test_accepts_a_zero_cooldown`, and add: `SCRAPE_COOLDOWN_SECONDS=-1` in the
      environment or `.env` is ignored.
- [x] `test_openapi.py`: the `/feed/home` description does not mention a refresh.
- [x] Delete `test_feed_home_refresher.py`. In `test_container.py`, drop the refresher from the
      resolve and close-order tests. Also remove
      `test_scraping_after_a_background_run_saves_only_what_that_run_did_not` from
      `test_scrape_feeds.py`, an I03 test built on the refresher. Phase 2 covers a manual run
      after a scheduled one.

### Implementation

- [x] Remove `refresher`, `clock` and `_is_from_a_previous_day` from `FeedHomeSearcher`.
- [x] Delete `feed_home_refresher.py` and the `feed_home_refresher` provider. Update the
      `FeedsProvider` docstring.
- [x] Remove `scrape_cooldown_seconds` from `Settings`.
- [x] Rewrite the `/feed/home` docstring in `routes/feed.py`.
- [x] Docs: add "Superseded by S10" notes to `S07` (stale-page refresh) and `I03` (background
      refresh and cooldown). Remove `SCRAPE_COOLDOWN_SECONDS` from `README.md` and
      `.env.example`.
- [x] Refactor without changing behavior. `BlockingFeedScrape` and `FixedClock` stay if other
      tests still use them.
- [x] Run the quality gate from `AGENTS.md` and fix failures. `home-feed.feature` and
      `scrap-feed.feature` pass.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Scheduled scraping

The scheduler use case, its two settings, its start in the lifespan and its cancellation on
shutdown, plus the OpenAPI copy and docs.

### Public contracts

- `contexts/cms/feeds/application/scrape/feed_scrape_scheduler.py`:

  ```python
  class FeedScrapeScheduler:
      def __init__(
          self,
          scraper: FeedScraper,
          interval: timedelta,
          wait: Callable[[timedelta], Awaitable[None]] = _sleep,
      ) -> None: ...
      def start(self) -> None: ...  # one task, kept in a strong reference; idempotent
      async def aclose(self) -> None: ...  # cancels and awaits the task, waiting or running
  ```

  The loop is: run (or skip if `scraper.is_running`) → `wait(interval)` → repeat. A run logs how
  many feeds it saved. A skip is logged. An `Exception` from a run is logged with
  `logger.exception` and the loop continues. Cancellation ends it.
- `Settings.scrape_schedule_enabled: bool = True` (`SCRAPE_SCHEDULE_ENABLED`) and
  `Settings.scrape_interval_seconds: float = Field(default=7200, gt=0)` (`SCRAPE_INTERVAL_SECONDS`).
- `IsolatedSettings` defaults `scrape_schedule_enabled=False`.
- `FeedsProvider.feed_scrape_scheduler(settings, scraper) -> AsyncIterator[FeedScrapeScheduler]`
  yields the scheduler and calls `aclose()` on close.
- Lifespan (`main.py`): after `STARTUP_DEPENDENCIES`, if `Settings.scrape_schedule_enabled`, then
  `(await container.get(FeedScrapeScheduler)).start()`.
- OpenAPI copy: the `/feed/scrap` docstring says it waits for a run in progress. `DESCRIPTION`
  says the five sources are scraped at startup and on a schedule.

### Tests first

- [ ] Fake `tests/contexts/cms/feeds/fakes/controlled_wait.py`: an async callable that records
      each interval and blocks until the test releases it, so no real sleeping happens.
- [ ] `test_feed_scrape_scheduler.py` (`FeedScraper` over `StubFeedScrape`/`BlockingFeedScrape` and
      `InMemoryFeedRepository`):
  - [ ] `start()` runs at once, then waits the interval, and after the wait runs again. Each
        wait starts after the previous run finished.
  - [ ] a run that is due while a manual `scraper.execute()` is in progress is skipped (no extra
        scrape call), the skip is logged, and the next wait is one interval.
  - [ ] a manual run during the wait does not end or restart the wait (still one recorded wait,
        and the next scheduled run happens only on release).
  - [ ] a run that raises (failing repository) is logged with its traceback and the schedule
        continues to the next wait and run.
  - [ ] each run logs the number of feeds it saved.
  - [ ] `aclose()` while waiting ends the task and no further run starts. `aclose()` while
        running cancels the run, keeps the feeds already saved, and no further run starts.
  - [ ] `start()` twice creates one task. `aclose()` without `start()` returns at once.
- [ ] `test_settings.py`: defaults `scrape_schedule_enabled is True` and
      `scrape_interval_seconds == 7200`. Both are read from the environment.
      `SCRAPE_INTERVAL_SECONDS` of `0` and `-1` is rejected.
- [ ] `test_app.py` (an override provider builds `FeedScraper` over a `BlockingFeedScrape`):
  - [ ] with the scheduler enabled, startup starts exactly one run and does not wait for it
        (`/status` answers while the scrape is blocked).
  - [ ] shutdown cancels the task before the HTTP and Mongo clients close (the scrape sees
        `CancelledError` while `http_client.is_closed` is still false).
  - [ ] with it disabled (the test default), no run starts.
- [ ] `test_container.py`: the scheduler resolves and closes before the HTTP client.
- [ ] `test_openapi.py`: the `/feed/scrap` description mentions waiting for a run in progress.
      The API description mentions scheduled scraping.

### Implementation

- [ ] Add `FeedScrapeScheduler` with the minimum loop that makes the use-case tests pass.
- [ ] Add the two settings and the `IsolatedSettings` default.
- [ ] Add the provider. In `create_app`'s lifespan, start the scheduler when enabled.
- [ ] Update the `/feed/scrap` docstring and `DESCRIPTION`.
- [ ] Docs: in `S00`, remove "Scheduler" from out of scope and add S10 to the table if it is
      missing. Add `SCRAPE_SCHEDULE_ENABLED` and `SCRAPE_INTERVAL_SECONDS` to `README.md` and
      `.env.example`. Set the S10 status to implemented.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures. `home-feed.feature` and
      `scrap-feed.feature` pass with the scheduler disabled.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Phase 1 is implemented. Review it and commit it with `/ai-project-conventional-commit`, then
run `/ai-project-implement-phase` for Phase 2.
