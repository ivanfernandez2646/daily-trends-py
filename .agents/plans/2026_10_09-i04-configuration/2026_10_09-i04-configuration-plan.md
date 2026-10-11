---
name: 'i04-configuration'
description: 'Settings load from the environment, a .env file and per-ENV defaults; scraping timeout and cooldown are configurable; "today" and "the same day" use an explicit business timezone'
spec: 'specs/improvements/I04-configuration.md'
branch: 'fix/i04-configuration'
created_at: '2026-10-09T14:00:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-11T09:25:47Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I04 · Configuration and business timezone

## Goal

Resolve improvements #1 and #18. Settings come from environment variables, then `.env`, then
defaults chosen by `ENV`, then global defaults. Invalid settings stop startup with exit code 1 and
never echo `MONGO_URL`. The scraping timeout and cooldown move from constants to settings. Front
page staleness and scraping deduplication compare calendar days in the `TIMEZONE` setting instead
of the server's zone or UTC. The repository stays green after each phase.

## Context

- Branch `fix/i04-configuration` is cut from `main`, which contains I01, I02 and I03. The I04 and
  I05 specs and the README links are uncommitted on the branch.
- `apps/cms_backend/settings.py`: `Settings(BaseSettings)` with `env`, `mongo_url` (one default) and
  `port`. It reads no `.env` file. `asgi.py` and `main()` build it with `Settings()`.
- `apps/cms_backend/main.py`: `create_app(settings, http_transport)` wires everything in `lifespan`.
  The constants `SCRAP_TIMEOUT_SECONDS = 10.0`, `SCRAP_USER_AGENT` and `SCRAP_COOLDOWN = 5 min` live
  there. `main()` logs `Startup failed` and exits 1 on any exception, including settings errors.
- Tests that would read a developer's `.env` today: `tests/apps/cms_backend/test_settings.py`
  (`Settings()`), `test_app.py` (`create_app(Settings())`), and `test_main.py`, which runs `main()` in a
  subprocess from the repo root. `tests/mongo.py` reads `MONGO_URL` from the process environment
  (CI sets it). The app fixture uses `Settings(mongo_url=TEST_MONGO_URL)`.
- Pydantic's `ValidationError` text includes the input of the failing validator. A model-level
  validator gets every field as input, so `MONGO_URL` could be printed. Value checks therefore live
  in field validators, and the production `MONGO_URL` rule raises an error whose text shows no
  input.
- `Clock` port: `now()` returns an aware datetime "in the server's local zone". `SystemClock` uses
  `datetime.now(UTC).astimezone()`. Test fake: `FixedClock(now)` with `advance()`.
- `FeedHomeSearcher._is_from_a_previous_day` already converts `createdAt` to `now.tzinfo`, so the
  business timezone reaches the front page through the clock alone.
- `FeedScraper._run` deduplicates by `(source, title, UTC day)` through
  `FeedRepository.exists_headline(source, title, day: date)`. `MongoFeedRepository` turns the day
  into the text range `[day, next day)` over `createdAt`, which is stored as UTC ISO text with
  milliseconds and `Z`. `InMemoryFeedRepository` compares UTC dates.
- Project `README.md` documents `ENV`, `MONGO_URL` (old default) and `PORT` in "Configuration".
- Spec notes go next to the rule they replace: S01 "Configuration", S07 "server local time", and
  I02 "the day is UTC".

## Phase 1: Configuration sources and scraping settings (#1)

Settings read `.env` and fill `MONGO_URL` from `ENV`. The scraping timeout and cooldown come from
settings. Tests never read `.env`.

### Public contracts

- `Settings` (pydantic-settings, `env_file=".env"`, case-insensitive):
  - `env: Literal["production", "dev", "test"] = "dev"`
  - `mongo_url: str`: when it is not set, it defaults to
    `mongodb://localhost:27017/daily-trends-dev` for `dev` and
    `mongodb://localhost:27017/daily-trends-test` for `test`. For `production` it is required: the
    error names `MONGO_URL` and has no value in it.
  - `port: int = 5000`
  - `scrap_timeout_seconds: float = 10`, must be > 0.
  - `scrap_cooldown_seconds: float = 300`, must be ≥ 0. `0` disables the cooldown.
- Composition root: the `httpx.AsyncClient` timeout is `settings.scrap_timeout_seconds`, and
  `FeedHomeRefresher` gets `timedelta(seconds=settings.scrap_cooldown_seconds)`. Only
  `SCRAP_USER_AGENT` stays a constant.
- `.env.example` (committed): every variable with its default, commented out.

### Tests first

- [x] `test_settings.py` (each test runs in `tmp_path` with the variables cleared):
  - no environment and no `.env` → the `dev` defaults, including `daily-trends-dev`;
  - `ENV=test` → the `daily-trends-test` URL;
  - `.env` with `PORT=5123` → 5123; the environment with `PORT=8080` as well → 8080;
  - `.env` with `ENV=test` only → the `test` URL;
  - an explicit `MONGO_URL` wins over the `ENV` default;
  - lower-case variable names are read;
  - `ENV=production` without `MONGO_URL` → `ValidationError` naming `MONGO_URL`;
  - a production error for another field, with `MONGO_URL=mongodb://user:secret@host/db`, does not
    contain `secret`;
  - `ENV=staging`, `PORT=abc`, `SCRAP_TIMEOUT_SECONDS=0`, `SCRAP_COOLDOWN_SECONDS=-1` → `ValidationError`;
  - `SCRAP_COOLDOWN_SECONDS=0` is accepted.
- [x] `test_main.py`: `ENV=production` without `MONGO_URL` exits 1 with `Startup failed`, and
      `MONGO_URL` is not in the output. Every `run_main` call runs in a temporary directory, so a
      `.env` in the repo root is never read.
- [x] App test (`integration`): a `/feed/home` refresh with `scrap_cooldown_seconds=0` starts a new
      background run right after the previous one finished.

### Implementation

- [x] Add `env_file`, the per-`ENV` `mongo_url` default, the scraping fields and their field
      validators to `Settings`.
- [x] Read the timeout and cooldown from settings in `create_app`. Remove `SCRAP_TIMEOUT_SECONDS` and
      `SCRAP_COOLDOWN`.
- [x] Isolate tests from `.env`: `test_settings.py` runs in `tmp_path`, and the app tests build
      `IsolatedSettings` (`tests/apps/cms_backend/isolated_settings.py`), a subclass with
      `env_file=None`. Pyright does not accept `_env_file` as a constructor argument, so the plan's
      `_env_file=None` became this subclass. The app fixture now goes through a `settings` fixture
      that tests can parametrize.
- [x] Add `.env.example`. Update the project `README.md` "Configuration" table: the new `MONGO_URL`
      defaults per `ENV`, the scraping variables, `.env` and the precedence.
- [x] Add a "Superseded by I04" note to the S01 "Configuration" section.
- [x] Run the quality gate from `AGENTS.md` with a `.env` whose `MONGO_URL` points elsewhere, and
      fix failures.
- [x] STOP for user review. Suggested commits:
  - `fix(i04): load settings from .env and per-environment defaults`
  - `fix(i04): make the scraping timeout and cooldown configurable`
  - `test(i04): keep the test suite independent of a local .env`

## Phase 2: Business timezone for the front page (#18)

`TIMEZONE` sets the zone of the system clock, so "today" for the front page is the business day.

### Public contracts

- `Settings.timezone: ZoneInfo`, read from `TIMEZONE`, default `Europe/Madrid`. An unknown name is
  a `ValidationError` naming `TIMEZONE`.
- `SystemClock(timezone: tzinfo)`: `now()` returns `datetime.now(timezone)`.
- `Clock.now()` docstring: the current time, aware, in the business timezone.
- Composition root: `SystemClock(settings.timezone)`.

### Tests first

- [x] `test_settings.py`: the default is `Europe/Madrid`; `TIMEZONE=America/New_York` is read;
      `TIMEZONE=Mars/Olympus` → `ValidationError`.
- [x] `test_main.py`: `TIMEZONE=Mars/Olympus` exits 1.
- [x] `test_system_clock.py`: `now()` is aware, its offset matches the configured zone, and it does
      not depend on `TZ`.
- [x] `test_feed_home_searcher.py`: newest feed at `2026-10-08T22:30:00.000Z`, clock fixed at
      `2026-10-09T08:00:00Z` in `Europe/Madrid` → fresh, no refresh requested. The same feed with
      the clock at `2026-10-10T08:00:00` Madrid → stale.

### Implementation

- [x] Add `timezone` to `Settings` (pydantic validates `ZoneInfo` natively, no custom validator), and `TIMEZONE` to `.env.example` and the
      README.
- [x] Give `SystemClock` its timezone and update the `Clock` docstring.
- [x] Wire `SystemClock(settings.timezone)` in `create_app`.
- [x] Add a "Superseded by I04" note next to "server local time" in S07.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggested commits:
  - `fix(i04): use an explicit business timezone for the front page`
  - `fix(i04): read the business timezone from settings`
  - `test(i04): cover front page staleness around local midnight`

## Phase 3: Business-day deduplication (#18)

Scraping deduplication compares calendar days in the business timezone. The repository receives
the day's bounds instead of a UTC date.

### Public contracts

- `FeedRepository.exists_headline(source: FeedSource, title: FeedTitle, since: datetime,
  until: datetime) -> bool`: whether a feed with this source and exact title was created at or
  after `since` and before `until`. Both bounds are aware.
- `MongoFeedRepository.exists_headline`: converts the bounds to UTC ISO text with milliseconds and
  `Z`, the stored format, and queries `createdAt` with `$gte` / `$lt`.
- `FeedScraper(repository: FeedRepository, scrapers: Sequence[FeedScrap], timezone: tzinfo)`: a
  feed's day is its `createdAt` in `timezone`. The bounds are that day's local midnight and the next
  day's local midnight, so DST days last 23 or 25 hours. The in-run duplicate key uses the same day.
- `InMemoryFeedRepository.exists_headline`: same range contract.
- Composition root: `FeedScraper(..., settings.timezone)`.

### Tests first

- [ ] `test_feed_scraper.py` with `Europe/Madrid`:
  - the same headline stored at `2026-10-08T21:30:00.000Z` and scraped at
    `2026-10-08T22:30:00.000Z` → saved (two business days);
  - stored at `2026-10-08T22:30:00.000Z` and scraped at `2026-10-09T21:00:00.000Z` → skipped (same
    business day);
  - on 25 October 2026 (clocks go back), stored at `2026-10-24T22:30:00.000Z` (00:30 local) and
    scraped at `2026-10-25T22:30:00.000Z` (23:30 local) → skipped;
  - the existing UTC-day tests are renamed to business-day tests with their dates adjusted.
- [ ] `test_mongo_feed_repository.py` (`integration`): a feed exactly at `since` is found, a feed
      exactly at `until` is not, and bounds given with a `+02:00` offset match the UTC-stored text.

### Implementation

- [ ] Change the `exists_headline` signature in the port, the Mongo repository and the in-memory
      fake.
- [ ] Add the `timezone` parameter to `FeedScraper` and compute the business day and its bounds.
- [ ] Pass `settings.timezone` to `FeedScraper` in `create_app`, and update the other places that
      build `FeedScraper`.
- [ ] Add a "Superseded by I04" note to the I02 rule "the day is UTC". Link I04 for #1 and #18 in
      `specs/improvements/README.md` (already done on the branch).
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggested commits:
  - `fix(i04): deduplicate scraped headlines by business day`
  - `fix(i04): pass day bounds to the headline lookup`
  - `test(i04): cover business-day deduplication across midnight and DST`

## Next step

Phases 1 and 2 are implemented. Run `/ai-project-implement-phase` to implement Phase 3.
