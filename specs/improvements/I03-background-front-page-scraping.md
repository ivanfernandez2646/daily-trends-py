# I03 · Background front-page scraping

**Status:** draft · **Fidelity:** intentional break with the ported behavior. Depends on S06, S07,
I01 and I02. Resolves improvements #4, #5 and #17 from `README.md`.

## Goal
Make `/feed/home` a fast read that never waits for external sites: when the front page is stale it
starts one scraping run in the background and answers with what is stored. At most one scraping run
happens at a time, so concurrent requests cannot store duplicate batches, and a recent run blocks
new background runs for a while, so failing sources are not retried on every request.

## Changes

### `/feed/home` no longer scrapes inside the request (#5)
- The staleness rule from S07 is unchanged: the home search returns results and the **newest** is
  from a day before today (day-level comparison, server local time).
- When the page is stale, `/feed/home` **requests a background refresh** and answers 200 at once with
  the feeds it found. It does not wait for the run and does not search again. Later requests
  see the scraped feeds once the run has saved them.
- When the search returns no results, no refresh is requested (unchanged from S07).
- Errors of a background run (a failing save, an unexpected exception) are logged and never reach
  any response. Before this change, a save error answered 500 on `/feed/home`.
- An error of the home search itself still answers 500 (unchanged, I01).

### One scraping run at a time (#17)
- All scraping runs in the process share one single-flight guard: the background refresh and
  `/feed/scrap`.
- A background refresh requested while any run is in progress (background or `/feed/scrap`) is
  **ignored**: no run is queued.
- `/feed/scrap` **waits** for a run in progress to finish, then performs its own run and answers with
  the feeds that this run saved (I01). Because runs no longer overlap, deduplication (I02) sees the
  previous run's feeds, so the waiting run usually saves nothing new.
- `/feed/scrap` keeps its error behavior: a save error answers 500.

### Cooldown between background runs (#4)
- A background refresh is **not started** if the previous background run **finished** less than
  **5 minutes** ago, whatever its outcome (feeds saved, nothing saved, every source failed, or an
  error).
- The cooldown is measured with the `Clock` port.
- `/feed/scrap` ignores the cooldown, and its runs do not start it: a manual run is always allowed
  and never blocks the next background refresh.
- The 5-minute value is a constant in the composition root, like the scraping timeout (I02).
  Making it configurable belongs to #1.

### Background task lifecycle
- The running task is kept in a strong reference until it finishes, as `AGENTS.md` requires.
- On application shutdown, a background run in progress is **cancelled and awaited** before the HTTP
  client and the Mongo client close. Feeds already saved by that run stay saved (no rollback, S06).
- A `/feed/scrap` request in progress at shutdown follows the server's normal request draining.

## Unchanged
- The home criteria, its response shape, and the rule that `CMS` feeds never appear (S07).
- Scraper behavior: selectors, the 5-per-source limit, the 10 s timeout, failing sources being
  dropped, deduplication by source + title + UTC day (S06, I02).
- "Today" uses the server's local timezone (#18 stays open).
- Everything in `README.md` outside #4, #5 and #17.

## Edge cases
- First request on a stale day → 200 with yesterday's feeds; a request after the run finishes → 200
  with today's feeds.
- Both sources fail → the run saves nothing; requests in the next 5 minutes answer the stale page
  without starting a run; the first request after the cooldown starts a new one.
- The scraping run saves nothing because every headline is a same-day duplicate (I02): the page stays
  stale, and the cooldown limits background runs to one every 5 minutes.
- Many concurrent `/feed/home` requests on a stale day → exactly one background run.
- `/feed/scrap` during a background run → it waits, runs, and answers `[]` when the sources have not
  changed in between.
- `/feed/home` during a `/feed/scrap` run → answers at once with stored feeds; no refresh is queued.
- The single-flight guard and the cooldown live in the process. Running several workers or replicas
  would allow one run per process (still deduplicated per run, but not across concurrent runs).
  The app is deployed as a single process (`daily-trends-py`).

## Acceptance criteria
- Use-case tests with a fixed clock and fake scrapers:
  - stale page → refresh requested, the response is the first search, one search only;
  - fresh page or empty result → no refresh requested;
  - a refresh requested while a run is in progress is ignored (one scraper call);
  - a refresh within 5 minutes of the previous run's end is ignored, one at exactly 5 minutes or later
    starts a run, after success and after failure;
  - a background run that raises is logged and does not propagate; the guard is released and the
    cooldown starts;
  - a manual run waits for a background run in progress, does not start the cooldown, and ignores it.
- The background run is executed as a task kept in a strong reference, and the app shutdown cancels it.
- Acceptance (`integration`): a stale `/feed/home` answers 200 with the stale feed; after the
  background run completes, `/feed/list` has 11 feeds and `/feed/home` returns the 10 scraped ones.
  When every source fails, `/feed/home` keeps answering the stale feed.
- `home-feed.feature` passes unchanged.
- `docs/openapi.yml` describes on `/feed/home` that a stale page triggers a background refresh and
  may be returned stale, and on `/feed/scrap` that it waits for a run in progress.
- `S07-front-page.md` gets a "Superseded by I03" note on the inline scraping and retry edge case;
  `README.md` links I03 for #4, #5 and #17.
