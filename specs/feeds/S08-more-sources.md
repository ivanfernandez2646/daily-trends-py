# S08 · More sources

**Status:** implemented · **Fidelity:** new capability. Depends on S06, S07, I02 and I03.

## Goal
Scrape three more Spanish newspapers, El Confidencial, La Razón and La Vanguardia, alongside El
Mundo and El Español, and keep the front page balanced: with five sources a run stores up to 25
feeds, so the front page shows the newest feeds of every source instead of whichever source was
saved last.

## Sources

### New `FeedSource` values
- `EL_CONFIDENCIAL`, `LA_RAZON` and `LA_VANGUARDIA` join `CMS`, `EL_PAIS`, `EL_MUNDO` and
  `EL_ESPANOL`. They are valid wherever a source is read: the domain, stored documents and the
  `source` enum of every response in the OpenAPI document.
- Feeds created through the API are still `CMS` (S02).

### Scrapers
Each new source has its own scraper with the same rules as the existing ones (S06, I02): walk the
`article` elements in order, take the trimmed text of each selector, skip an article without author
or title, at most **5 per source**, a blank description is `null`, the page is decoded with its
declared charset, 10 s timeout, `User-Agent: daily-trends-py`, redirects followed, a non-2xx page
parsed like any other.

| Source | URL | Author | Title | Description |
|---|---|---|---|---|
| El Confidencial (`EL_CONFIDENCIAL`) | `https://www.elconfidencial.com/` | `.articleByline__signature` | `.titleArticleEditable` | `.teaser__leadin` |
| La Razón (`LA_RAZON`) | `https://www.larazon.es/` | `.article__author` | `.article__title` | `.article__summary` |
| La Vanguardia (`LA_VANGUARDIA`) | `https://www.lavanguardia.com/` | `.author-name, .author` | `.title` | `.subtitle` |

- No per-source cleanup: the text is stored as extracted. Bylines that carry a place or a second
  name stay as they are (`"Eusebio Val | París"`, `"Marcos Lamelas. Barcelona"`).
- El Confidencial rarely shows a lead-in on its front page, so most of its feeds have a `null`
  description.
- The selectors were checked on 2026-10-20 against the live front pages with the app's own client:
  each returned 200 and yielded 5 feeds with author and title.

> **Superseded by [S18](S18-varied-categories.md):** each scraper selects up to 15 feeds, at most 2
> per category, so a run stores at most 75.

### Scraping runs
- Every scraping run (`/feed/scrap` and the background refresh, I03) runs the **five** scrapers in
  parallel. One failing or timing-out source is dropped and logged; the others are saved (S06).
- A run stores at most 25 feeds. Deduplication by source + title + day (I02) applies per source as
  before.
- The single-flight guard and the cooldown (I03) are unchanged: they cover the whole run, not each
  source.

## Front page (`GET /feed/home`)
Replaces the home search of S07 (`EL_MUNDO OR EL_ESPANOL`, newest 10).

- **Home sources:** `EL_MUNDO`, `EL_ESPANOL`, `EL_CONFIDENCIAL`, `LA_RAZON` and `LA_VANGUARDIA`. `CMS`
  and `EL_PAIS` feeds never appear.
- **Selection:**
  1. For each home source, its **2** newest feeds (by `createdAt`).
  2. If that gives fewer than **10** feeds (a source has fewer than 2 stored feeds), the free slots are
     filled with the newest remaining feeds of any home source.
  3. The result is at most 10 feeds, ordered by `createdAt` descending. Feeds with the same
     `createdAt` (one scraper's batch) have no guaranteed order among themselves.

> **Superseded by [S18](S18-varied-categories.md):** the selection picks at most 2 feeds per source
> and 2 per category among the 15 newest of each source, then fills up to 10.
- **Staleness** (S07, I03, I04) is unchanged: the newest feed of the result is the newest home feed
  overall, and the page is stale when it is from a day before today in the business timezone.
- No results → `[]` and no refresh (unchanged).
- The 2-per-source and 10 values are constants of the home use case, like the 5-per-source limit.
  Making them configurable is out of scope.

## Unchanged
- Every other route and its contract. `/feed/scrap` still answers the feeds saved by this run (I01),
  now up to 25.
- The background refresh rules (I03), the business timezone (I04), the indexes (I08). The existing
  `source: 1, createdAt: -1` index serves the per-source selection; no migration is needed.
- `EL_PAIS` is still not scraped (S06).

## Edge cases
- Only El Mundo has stored feeds (12 of them) → the home page shows its 10 newest (2 from step 1,
  8 from the fill).
- La Razón fails on a run → the page shows 2 from each of the other four sources and fills 2 slots
  with the next newest of any of them; La Razón's older feeds, if any, still count for step 1.
- A source whose 2 newest feeds are a week old still gets 2 slots, ahead of newer feeds of other
  sources beyond their 2. The page is stale only if the newest of all is from a previous day.
- A source's front page changes its markup → it yields no feeds and the run saves the others; the
  live smoke test of that scraper fails.

## Acceptance criteria
- Domain: the three new `FeedSource` values are accepted; an unknown value is still an invalid
  argument.
- One scraper test per new source with a hand-written HTML fixture: selectors, skipping, the
  5-per-source limit, `null` description, the stored source.
- One live smoke test per new scraper (marker `network`): 5 feeds with that source and non-empty
  author and title.
- Use-case tests for the home search with the in-memory fake:
  - 2 per source when every source has enough feeds, ordered by `createdAt` descending;
  - the fill when a source has fewer than 2, up to 10 in total;
  - `CMS` and `EL_PAIS` feeds never appear;
  - staleness still uses the newest feed of the result.
- Repository integration test against real Mongo for the per-source selection.
- The composition root wires the five scrapers; the acceptance harness (`FrontPagesTransport`) serves
  a fixture for each of the five front pages.
- `scrap-feed.feature`: the first `/feed/scrap` answers 25 feeds, `/feed/home` 10, `/feed/list` 27;
  the second `/feed/scrap` answers `[]` and `/feed/list` stays at 27.
- `home-feed.feature` passes unchanged.
- The OpenAPI document lists the new sources and describes the per-source selection on `/feed/home`.
- `S00` lists the new sources in its glossary and S08 in its table; `S06` and `S07` get a "See S08"
  note on the scraped sources and on the home search.
