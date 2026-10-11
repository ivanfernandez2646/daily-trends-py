# I04 · Configuration and business timezone

**Status:** draft · **Fidelity:** intentional break with the ported behavior. Depends on S01, S06,
S07, I02 and I03. Resolves improvements #1 and #18 from `README.md`.

## Goal
Configuration comes from one place with a clear precedence: environment variables, then a local
`.env` file, then defaults that depend on `ENV`, as the original `dev.json` / `test.json` meant to do.
"Today" and "the same day" use an explicit business timezone from settings instead of the
server's `TZ`.

## Changes

### Sources and precedence (#1)
- Settings are read, from highest to lowest priority, from:
  1. process environment variables;
  2. a `.env` file in the working directory, if it exists (a missing file is not an error);
  3. defaults for the current `ENV`;
  4. global defaults.
- `ENV` itself can come from the environment or from `.env`, and it selects the defaults in level 3.
- Variable names are case-insensitive, as they are today.
- The test suite never reads `.env`: tests build their settings explicitly, so a developer's
  `.env` cannot point the tests at another database.
- A `.env.example` listing every variable with its default is committed. `.env` stays git-ignored.

### Variables
| Variable | Type | Default | Notes |
|---|---|---|---|
| `ENV` | `production` \| `dev` \| `test` | `dev` | Unchanged. |
| `MONGO_URL` | string | `dev`: `mongodb://localhost:27017/daily-trends-dev`; `test`: `mongodb://localhost:27017/daily-trends-test`; `production`: **none** | The `dev` and `test` values are the ones in the original `dev.json` / `test.json`. Production must set it. |
| `PORT` | integer | `5000` | Unchanged. |
| `TIMEZONE` | IANA zone name | `Europe/Madrid` | Business timezone (#18). Both sources are Spanish newspapers. |
| `SCRAP_TIMEOUT_SECONDS` | number > 0 | `10` | Was a constant in the composition root (I02). |
| `SCRAP_COOLDOWN_SECONDS` | number ≥ 0 | `300` | Was a constant in the composition root (I03). `0` disables the cooldown. |

- The scraping `User-Agent` stays a constant. It identifies the app and is not a deployment choice.
- Invalid configuration fails at startup, following the S01 rule: the error is logged and the
  process exits with code 1. Invalid means an unknown `ENV`, a `PORT` that is not an integer, an
  unknown `TIMEZONE`, a non-positive timeout, a negative cooldown, or `ENV=production` with no
  `MONGO_URL`.
- The error message names the variable and does not echo `MONGO_URL`, because it can contain
  credentials.

### Business timezone (#18)
- The `Clock` returns the current time in the business timezone instead of the server's local
  zone. `TZ` no longer changes any behavior.
- **Front page staleness (S07, I03):** "the newest feed is from a day before today" compares
  calendar days in the business timezone.
- **Scraping deduplication (I02):** "the same day" is the calendar day in the business timezone,
  not the UTC day. A day starts at local midnight and ends at the next local midnight, so DST days
  last 23 or 25 hours.
- Storage and responses do not change: dates are still stored and returned as UTC ISO-8601 with
  milliseconds and `Z` (S02).

## Unchanged
- Defaults for `ENV` and `PORT`, and the fact that environment variables override everything.
- Every HTTP contract, the staleness and cooldown rules other than the zone they use, the
  single-flight guard (I03), and the scrapers.
- Everything in `README.md` outside #1 and #18.

## Edge cases
- `.env` sets `PORT=5123` and the environment sets `PORT=8080` → port 8080.
- `.env` sets `ENV=test` and nothing else → `MONGO_URL` defaults to the `test` database.
- `ENV=production` with no `MONGO_URL` → startup fails with exit code 1 and a message naming
  `MONGO_URL`.
- `TIMEZONE=Mars/Olympus` → startup fails with exit code 1.
- Business timezone `Europe/Madrid`, newest feed at `2026-10-08T22:30:00.000Z` (00:30 on 9 October
  in Madrid), now `2026-10-09T08:00:00Z` → the page is **fresh**. Under the UTC rule it was stale.
- The same headline scraped at `2026-10-08T21:30:00.000Z` and `2026-10-08T22:30:00.000Z` (23:30 and
  00:30 in Madrid) → two different business days, so both are saved. Under the UTC rule the second
  one was dropped.
- On the night clocks go back (25-hour day), headlines from 00:00 to 24:00 local time count as one
  day.

## Acceptance criteria
- Settings tests cover each precedence level, the per-`ENV` defaults, every invalid value above,
  and that the production error does not contain `MONGO_URL`'s value.
- A startup test checks that invalid settings exit with code 1.
- `SystemClock` returns an aware `datetime` in the configured zone.
- Front page use-case tests with a fixed clock in `Europe/Madrid` cover the local-midnight case
  above.
- Scraper use-case and repository integration tests cover the two-business-day case and a DST day.
- The composition root reads the timeout, cooldown and timezone from settings. No scraping
  constant except the `User-Agent` is left in it.
- Tests build settings without `.env`. The quality gate passes with a `.env` present that points
  `MONGO_URL` elsewhere.
- `.env.example` is committed. `README.md` (project) documents the variables.
- `S01-foundation.md` gets a "Superseded by I04" note on configuration, `S07-front-page.md` on
  "server local time", and `I02` on the UTC day. `README.md` links I04 for #1 and #18.
