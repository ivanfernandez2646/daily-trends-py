---
name: 's08-more-sources'
description: 'Scrape El Confidencial, La Razón and La Vanguardia alongside El Mundo and El Español, and balance the front page with the 2 newest feeds of each home source plus a newest-first fill up to 10'
spec: 'specs/feeds/S08-more-sources.md'
branch: 'feat/s08-more-sources'
created_at: '2026-10-20T15:16:05Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-20T16:10:00Z'
implemented_at: '2026-10-20T16:10:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S08 · More sources

## Goal

A scraping run reads five front pages and stores up to 25 feeds. `GET /feed/home` shows the newest
feeds of every home source rather than only those of the source saved last.

## Context

- `FeedSource` (`contexts/cms/feeds/domain/value_objects.py`) is a `StrEnum`, and `_missing_`
  raises `InvalidArgumentError`. The response schema's `source: FeedSource` gives the OpenAPI enum,
  so new members show up there with no other change.
- Every scraper is a `ScrapeMapping` plus a thin class that calls `scrape_front_page`
  (`infrastructure/scrape/front_page.py`). That function already has the shared rules: the
  `article` walk, trimming, skipping, the 5-per-source limit, `null` descriptions and charset
  decoding. The new scrapers do no per-source cleanup, so they keep the default `clean_description`.
- `FeedsProvider.feed_scraper` (`apps/cms_backend/providers/feeds.py`) lists the scrapers. The
  shared `httpx.AsyncClient` already sets the 10 s timeout, the User-Agent and redirects.
- `tests/scrape_fixtures.py` `FrontPagesTransport` serves `tests/fixtures/scrape/<name>.html` by
  host, with the charset the real site declares.
- `FeedHomeSearcher` (`application/home/feed_home_searcher.py`) runs one `HOME_CRITERIA` search
  (`EL_MUNDO OR EL_ESPANOL`, newest 10). Its staleness check uses `feeds[0]`.
- **Agreed:** the per-source selection uses the existing `FeedRepository.search` with
  `FeedCriteria`. It runs one search per home source (limit 2) and one newest-10 search over all
  home sources for the fill, all in parallel. The port, the fakes and the Mongo adapter stay
  unchanged, and the `source: 1, createdAt: -1` index serves each search.
- Fill correctness: at most `k` of the 10 newest home feeds were already picked in step 1 (`k` ≤
  10). That leaves at least `10 − k` unpicked feeds, enough to fill the free slots.

## Phases

## Phase 1: Three new sources

The domain accepts `EL_CONFIDENCIAL`, `LA_RAZON` and `LA_VANGUARDIA`. Each one has a scraper with
the selectors from the spec, and the composition root runs all five scrapers. `/feed/home` keeps
its S07 query in this phase. It still answers 10, so `scrap-feed.feature` passes with the new
totals.

### Public contracts

- `FeedSource.EL_CONFIDENCIAL = "EL_CONFIDENCIAL"`, `FeedSource.LA_RAZON = "LA_RAZON"`,
  `FeedSource.LA_VANGUARDIA = "LA_VANGUARDIA"`. They also appear in the OpenAPI `source` enum of
  every response.
- `ElConfidencialFeedScraper(client: httpx.AsyncClient, clock: Clock)` with
  `async scrape() -> list[Feed]`. It reads `https://www.elconfidencial.com/` with
  `.articleByline__signature` / `.titleArticleEditable` / `.teaser__leadin`.
- `LaRazonFeedScraper(client, clock)`. It reads `https://www.larazon.es/` with `.article__author` /
  `.article__title` / `.article__summary`.
- `LaVanguardiaFeedScraper(client, clock)`. It reads `https://www.lavanguardia.com/` with
  `.author-name, .author` / `.title` / `.subtitle`.
- `FeedScraper` is wired with the five scrapers. `/feed/scrap` answers up to 25 feeds.
- Test harness: `FrontPagesTransport` serves `el_confidencial.html`, `la_razon.html` and
  `la_vanguardia.html` for `www.elconfidencial.com`, `www.larazon.es` and `www.lavanguardia.com`,
  each with the charset its live site declares.

### Tests first

- [x] `test_feed_value_objects.py`: each new source parses from its string value, and an unknown
      value still raises `InvalidArgumentError`.
- [x] `test_el_confidencial_feed_scraper.py`, `test_la_razon_feed_scraper.py` and
      `test_la_vanguardia_feed_scraper.py`, modeled on the El Español test, each with a
      hand-written fixture:
  - requests the front page URL;
  - scrapes 5 feeds in order (author, title), skipping articles without author or title, and
    ignores a 6th valid article;
  - a missing or blank description is `None`;
  - every feed has its own source, was created now and records one `FeedCreatedDomainEvent`;
  - text is stored as extracted. The fixtures include `"Eusebio Val | París"`-style bylines (La
    Vanguardia) and `"Marcos Lamelas. Barcelona"`-style bylines (El Confidencial);
  - La Vanguardia: the author comes from either `.author-name` or `.author`;
  - live smoke test (`@pytest.mark.network`): 5 feeds with that source and non-empty author and
    title.
- [x] ~~`test_container.py`: the app's `FeedScraper` holds the five scrapers.~~ Covered instead by
      `test_scrape_feeds.py::test_scraping_reads_the_five_front_pages`: the scraper list is
      private, and the requested hosts are the observable behavior.
- [x] `test_scrape_feeds.py` (app level): a run answers the feeds of all five sources. If one host
      fails or times out, the other four are saved.
- [x] `scrap-feed.feature`: the first `/feed/scrap` answers 25, `/feed/home` 10 and `/feed/list`
      27. The second `/feed/scrap` answers 0 and `/feed/list` stays at 27.
- [x] `test_openapi.py`: the `source` enum lists the seven values.

### Implementation

- [x] Add the three `FeedSource` members.
- [x] Add `el_confidencial_feed_scraper.py`, `la_razon_feed_scraper.py` and
      `la_vanguardia_feed_scraper.py` under `infrastructure/scrape/`, each a `ScrapeMapping` and a
      class like `ElEspanolFeedScraper`.
- [x] Add the three HTML fixtures and register them in `FrontPagesTransport._FRONT_PAGES`, with the
      charset each live site declares (checked with the app's client).
- [x] Wire the five scrapers in `FeedsProvider.feed_scraper`.
- [x] `FeedSourceMother` picks from all values if it does not already (it already did).
- [x] Specs: S00 adds the new sources to its glossary and S08 to its table. S06 gets a
      "See S08" note on the scraped sources.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures. Run `uv run pytest -m network` for
      the five smoke tests. The El Confidencial smoke test sends `User-Agent: daily-trends-py`:
      the site answers 403 to httpx's default one.
- [x] Existing app tests that assumed two sources were updated: the one-source-fails tests
      expect the other four sources (20 feeds), and the stored totals after a run are 26.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Balanced front page

`GET /feed/home` takes the 2 newest feeds of each home source and fills the free slots with the
newest remaining home feeds, up to 10 ordered by `createdAt` descending. Staleness still uses the
newest feed of the result.

### Public contracts

- `FeedHomeSearcher.execute() -> list[Feed]`: the signature is unchanged and the selection is
  new.
- Module constants in `feed_home_searcher.py` replace `HOME_CRITERIA`: `HOME_SOURCES =
  (EL_MUNDO, EL_ESPANOL, EL_CONFIDENCIAL, LA_RAZON, LA_VANGUARDIA)`, `FEEDS_PER_SOURCE = 2`,
  `HOME_LIMIT = 10`.
- OpenAPI: the `/feed/home` description describes the per-source selection, for example: "The 2
  newest feeds of each external source, filled with the newest of any of them up to 10, newest
  first; a stale front page is refreshed in the background."

### Tests first

- [x] `test_feed_home_searcher.py` with the in-memory fake:
  - each home source has 3 or more feeds → 2 per source (10), ordered by `createdAt`
    descending, and each source's third feed is left out even when it is newer than the others;
  - only El Mundo has 12 feeds → its 10 newest;
  - one source has none and another has 1 → the free slots go to the newest remaining home
    feeds, 10 in total;
  - fewer than 10 home feeds in total → all of them;
  - a source whose 2 newest feeds are a week old still gets its 2 slots ahead of newer third
    feeds of other sources;
  - `CMS` and `EL_PAIS` feeds never appear, even when they are the newest;
  - staleness: a week-old source does not make the page stale while the newest feed is from
    today. The page is stale when the newest feed of the result is from a previous day. The
    existing staleness tests stay.
  - Replace `test_returns_the_ten_newest_external_feeds_without_cms_or_other_sources`, which
    encodes the S07 selection.
- [x] `test_mongo_feed_repository.py` (real Mongo): a single-source search with `created_at`
      descending and limit 2 returns only that source's 2 newest feeds.
- [x] `test_home_feeds.py` (app level): after a five-source scrape, `/feed/home` answers 2 from
      each source; with three stored feeds per source and a newer `CMS` one, it answers the 2
      newest of each (replaces the S07 ten-newest test).
- [x] `home-feed.feature` passes unchanged.
- [x] `test_openapi.py`: the `/feed/home` description mentions the per-source selection, if the
      suite checks route descriptions.

### Implementation

- [x] `FeedHomeSearcher.execute`: run `asyncio.gather` over one `FeedCriteria(filters=(source,),
      order=created_at desc, limit=FEEDS_PER_SOURCE)` per home source and one newest-`HOME_LIMIT`
      search over all home sources. Merge the per-source picks, append unpicked feeds from the
      newest search until `HOME_LIMIT`, sort by `created_at` descending and keep `feeds[0]` for
      staleness.
- [x] Update the `/feed/home` route docstring.
- [x] The two cooldown tests in `test_home_feeds.py` and the every-source-fails scrape test now
      fail every host through `EVERY_FRONT_PAGE_HOST` (`tests/scrape_fixtures.py`). They named
      only El Mundo and El Español, so after Phase 1 the other three sources still answered.
- [x] Specs: S07 gets a "See S08" note on the home search, and the S00 glossary's "Front page"
      entry describes the per-source selection.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Both phases are implemented. Review Phase 2, then commit it with `/ai-project-conventional-commit`.
