# S10 · Scheduled scraping

**Status:** implemented · **Fidelity:** new capability; replaces the front-page background refresh of I03.
Depends on S06, S07, S08, I02, I03 and I04.

## Goal
Keep the scraped feeds fresh on a fixed schedule instead of on demand: the app scrapes every source
when it starts and then every 2 hours, whatever the traffic. `/feed/home` becomes a plain read, and
`/feed/scrap` keeps working as the manual refresh it is today.

## Scheduled runs

### Cadence
- When the app starts, after the startup dependencies are ready (Mongo reachable, migrations
  applied), a scheduled run starts **at once**, in the background: startup does not wait for it and
  the app takes traffic meanwhile.
- After each scheduled run **finishes**, or is **skipped** (see below), the scheduler waits the
  interval, **2 hours** by default, and starts the next one. Runs therefore never overlap, and the
  time between two starts is the interval plus the previous run's duration.
- A scheduled run is the same run as `/feed/scrap` (S06, S08, I02): the five sources in parallel, a
  failing or timing-out source dropped and logged, deduplication by source + title + day.
- Restarting the app starts a new cycle with an immediate run. Deduplication keeps frequent restarts
  from storing the same headlines twice on the same day.

### Interaction with `/feed/scrap`
- Scheduled runs and `/feed/scrap` share the single-flight guard of I03: one scraping run at a time
  in the process.
- When a scheduled run is due while a `/feed/scrap` run is in progress, the scheduled run is
  **skipped**: nothing is queued, the skip is logged, and the next scheduled run is one interval
  later.
- `/feed/scrap` during a scheduled run **waits** for it, then performs its own run and answers the
  feeds that this run saved, usually `[]` (unchanged from I03).
- A `/feed/scrap` run **does not reset** the schedule: the next scheduled run keeps its time.

### Errors
- An error of a scheduled run (a failing save, an unexpected exception) is logged with its traceback
  and never stops the schedule: the scheduler waits the interval and runs again.
- Feeds saved before the error stay saved (no rollback, S06).
- Each scheduled run logs how many feeds it saved.

### Lifecycle
- The scheduler is one `asyncio` task kept in a strong reference (`AGENTS.md`), started by the app's
  lifespan.
- On shutdown the task is **cancelled and awaited**, whether it is waiting or running, before the
  HTTP client and the Mongo client close. A run cancelled mid-way keeps the feeds it already saved.
- The app is deployed as a single process (I03). Several workers or replicas would each run their
  own schedule; deduplication limits the effect to repeated work, not repeated feeds, except for
  runs that overlap across processes (#17 in `improvements/README.md`).

### Configuration (I04)
| Variable | Default | Rule |
|---|---|---|
| `SCRAPE_SCHEDULE_ENABLED` | `true` | `false` starts no scheduler: scraping only happens through `/feed/scrap`. |
| `SCRAPE_INTERVAL_SECONDS` | `7200` | Greater than 0; an invalid value stops startup like any invalid setting. |

- The test settings disable the scheduler, so tests never hit it by accident.

## Front page (`GET /feed/home`)
Replaces the stale-page rules of S07 and I03.

- `/feed/home` only reads: it answers the selection of S08 and **never** starts a scraping run,
  whatever the age of its newest feed.
- The staleness rule (newest feed from a day before today), the background refresh and its cooldown
  are **removed**. `SCRAPE_COOLDOWN_SECONDS` is no longer a setting; a leftover value in the
  environment is ignored like any unknown variable.
- No results → `[]` (unchanged).

## Unchanged
- `/feed/scrap`: route, response and errors (I01, I03). It stays the manual refresh.
- The scraping rules, sources and timeout (S06, S08, I02), the front-page selection (S08), the
  business timezone (I04), deduplication.

## Edge cases
- The app starts with an empty database → the first scheduled run fills it; `/feed/home` answers `[]`
  until the run saves its feeds.
- Every source fails in a scheduled run → nothing is saved, the failures are logged, the next run is
  2 hours later. `/feed/home` keeps answering the stored feeds.
- Startup at 10:00, run until 10:00:08 → next at about 12:00:08. A `/feed/scrap` at 11:00 does not
  move it. A `/feed/scrap` in progress at 12:00:08 → that scheduled run is skipped, the next one is
  at about 14:00:08.
- Shutdown during the 2-hour wait → the task is cancelled at once, no run starts.
- Shutdown during a scheduled run → the run is cancelled; feeds it already saved stay.
- `SCRAPE_SCHEDULE_ENABLED=false` → behavior equals I03 without the home refresh: feeds only arrive
  through `/feed/scrap`.

## Acceptance criteria
- Use-case tests for the scheduler with a fake scraper and an injectable wait (no real sleeping):
  - a run starts immediately, then one per interval after the previous one finishes;
  - a due run while a manual run is in progress is skipped and the next one is one interval later;
  - a manual run does not change the time of the next scheduled run;
  - a run that raises is logged and the schedule continues;
  - cancelling the scheduler while waiting or while running ends it, and no further run starts.
- The home use case never calls the scraper: stale, fresh and empty pages are plain searches.
- App tests: with the scheduler enabled, startup starts exactly one run and does not wait for it;
  shutdown cancels the task before the clients close; with it disabled, no run starts.
- Settings tests: the two variables, their defaults, `SCRAPE_INTERVAL_SECONDS <= 0` rejected,
  `SCRAPE_COOLDOWN_SECONDS` ignored.
- `home-feed.feature` and `scrap-feed.feature` pass with the scheduler disabled.
- The I03 tests for the background refresh and cooldown are removed along with the code.
- The OpenAPI document no longer says that `/feed/home` triggers a refresh; it says that feeds are
  scraped on a schedule and that `/feed/scrap` waits for a run in progress.
- `S07` and `I03` get a "Superseded by S10" note on the stale-page refresh and the cooldown; `S00`
  removes "scheduler" from out of scope and adds S10 to its table; `.env.example` (if any) and the
  README document the two variables.
