---
name: 's18-varied-categories'
description: 'Each scraper keeps up to 15 feeds of its front page, at most 2 per category, and the front page picks at most 2 per source and 2 per category'
spec: 'specs/feeds/S18-varied-categories.md'
branch: 'feat/s18-varied-categories'
created_at: '2026-10-23T10:22:34Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-23T10:55:48Z'
implemented_at: '2026-10-23T10:55:48Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S18 · Varied categories

## Goal

Stored feeds and the front page show news of every kind, not only the political opening of each
newspaper:

- Each scraper selects up to 15 articles from the page it already downloads, at most 2 per category.
  It walks the page in rounds: first the first article of each category, then the second.
- `/feed/home` picks at most 2 feeds per source and 2 per category from the 15 newest feeds of each
  source. It fills up to 10 when there is not enough variety.
- The category tables map sections that came out as `OTHER`.

No route, field, schema, setting or migration changes.

## Context

- **Scraping today:**
  - `extract_feeds` ([front_page.py](../../../src/daily_trends_py/contexts/cms/feeds/infrastructure/scrape/front_page.py))
    walks the `article` elements in order.
  - It calls `Feed.create` for each usable one (author, title and an `http(s)` link) and stops at
    `MAX_FEEDS_PER_SOURCE = 5`.
  - The category comes from `_category(url, mapping.categories)`.
- **Selection before creation (agreed):**
  - `extract_feeds` first collects lightweight candidates, each with its author, title, description,
    URL and category.
  - It selects among them and only then creates the feeds.
  - El Español has about 250 usable articles, and creating a `Feed` records a
    `FeedCreatedDomainEvent` that would be discarded.
  - The candidate type is private to `front_page.py`.
- **Deduplication:** it stays in `FeedScraper` (application) and runs after the selection, as the spec
  says. `FeedScraper` does not change.
- **Fixtures:**
  - Each fixture in `tests/fixtures/scrape/` has 6 usable articles, and none has more than 2 of one
    category. The new rules would select all of them.
  - Agreed: add 3 `POLITICS` articles to `el_espanol.html` so the cap shows end to end. It then has
    9 usable articles and 7 are selected: `POLITICS` 2, `OTHER` 2, `SOCIETY`, `ECONOMY` and
    `TECHNOLOGY`.
  - `scrap-feed.feature` becomes 31 scraped feeds, 4 `SPORTS`, 10 on the home page and 33 in the
    list.
- **Home today:**
  - `FeedHomeSearcher` runs one search per source (`limit=2`) and one "newest 10 of any home source"
    search for the fill.
  - With the new rules the candidates are 5 searches with `limit=15`. Step 2 fills from those
    candidates, so the global search goes away.
  - The existing search by source with order and limit serves them, so no repository change and no
    new Mongo test are needed.
- **Ties:**
  - Feeds of one batch share `created_at`.
  - The walk goes newest first with a stable sort, so ties keep the order the repository answered.
  - Tests use distinct `created_at` values wherever order matters.
- **Unchanged tests:**
  - `home-feed.feature`: 2 feeds of different sources and categories.
  - The web e2e `front-page.spec.ts`: 10 `POLITICS` feeds, 2 per source. Step 1 picks 2 of them and
    step 2 fills the other 8, ordered by `created_at` as before.
- **Docs:** S00, S08 and S09 already carry their notes about S18. Only S18's status changes, at the
  end.

## Phases

## Phase 1: Varied scraping and category tables

Each scraper stores up to 15 feeds, at most 2 per category, in page order. The tables map the new
sections. The front page keeps the S08 selection in this phase.

### Public contracts

- `front_page.py`:
  - `MAX_FEEDS_PER_SOURCE = 15`, up from 5.
  - New constant `MAX_FEEDS_PER_CATEGORY = 2`.
- `extract_feeds(html, mapping, now, page_url) -> list[Feed]`:
  - The signature does not change.
  - It returns the selection in page order.
  - The first round takes the first article of each category, and the second round the second one.
  - Articles without author, title or a usable link are skipped before the selection.
- Category tables (`_MAPPING.categories`):
  - El Mundo: `pais-vasco` and `aragon` → `SOCIETY`; `la-lectura` → `CULTURE`.
  - El Español: `el-cultural` → `CULTURE`.
  - El Confidencial: `television` → `CULTURE`; `inmobiliario` → `ECONOMY`.
  - La Razón: `television` → `CULTURE`; `tecnologia-consumo` → `TECHNOLOGY`.
- Test fixture `tests/fixtures/scrape/el_espanol.html` gains 3 `POLITICS` articles.
- `scrap-feed.feature` changes its counts:
  - `/feed/scrap` answers 31 feeds;
  - `?category=SPORTS` gives 4;
  - `/feed/home` gives 10;
  - `/feed/list` gives 33, then still 33 after the second `/feed/scrap` answers `[]`.

### Tests first

- [x] `test_front_page.py`, with hand-written articles:
  - [x] Pages with categories A, A, B, A, C, B give A1, B1, C1 in the first round and A2, B2 in the
    second, returned in page order: A1, A2, B1, C1, B2.
  - [x] At most 2 per category, `OTHER` included: links to unmapped sections count as one
    category.
  - [x] A page whose articles all share one category gives 2 feeds.
  - [x] 3 categories of 5 articles each give 6 feeds.
  - [x] At most 15 per source. There are only 10 categories besides `OTHER`, so the test uses
    10 categories × 2 articles: all 10 firsts plus the first 5 seconds, in page order.
  - [x] Unusable articles (without author, title or link) do not count toward a category's quota.
  - [x] Replace `test_stops_at_five_feeds` with the 15 limit. The test that skips articles without
    a usable link now uses two categories.
- [x] Scraper tests:
  - [x] Add the new sections to `test_maps_its_sections_to_categories` of El Mundo, El Español, El
    Confidencial and La Razón.
  - [x] The fixture tests become "scrapes six feeds", and "scrapes seven feeds keeping two of its
    four political ones" for El Español with the extended fixture.
- [x] Live smoke tests (marker `network`): each source yields between 1 and 15 feeds, at most 2 per
  category, each with an `http(s)` URL and a category. They passed against the live front pages on
  2026-10-23.
- [x] `scrap-feed.feature`: the new counts. `test_scrape_feeds.py` too: 31 with every source, 25
  without El Mundo.

### Implementation

- [x] Split `extract_feeds` into collecting `_Teaser`s, a `_varied` selection and creating the feeds
  of the selection.
- [x] Add the new sections to the four scrapers' tables.
- [x] Extend `el_espanol.html` with 3 `POLITICS` articles (two under `/espana/`, one under
  `/politica/`). Every fixture's last article was titled *Esta sexta noticia válida no se guarda*;
  it is now saved, so it is retitled *Una noticia sin sección también se guarda* (El Mundo's in
  ISO-8859-1).
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Front page that mixes categories, and docs

`/feed/home` picks at most 2 feeds per source and 2 per category among the 15 newest of each source,
fills up to 10, and its OpenAPI description says so.

### Public contracts

- `FeedHomeSearcher.execute() -> list[Feed]`:
  - The signature does not change.
  - Candidates: for each home source, a search with `limit=CANDIDATES_PER_SOURCE`, newest first.
  - Step 1 walks all the candidates newest first. It picks a feed while fewer than
    `FEEDS_PER_SOURCE` of its source and fewer than `FEEDS_PER_CATEGORY` of its category are
    picked, until `HOME_LIMIT`.
  - Step 2 walks the candidates again and picks any feed not yet picked, until `HOME_LIMIT`.
  - The result is sorted by `created_at` descending.
- Constants of the home use case: `CANDIDATES_PER_SOURCE = 15`, `FEEDS_PER_SOURCE = 2`,
  `FEEDS_PER_CATEGORY = 2`, `HOME_LIMIT = 10`.
- `GET /feed/home` keeps its route and response. Its description in
  [feed.py](../../../src/daily_trends_py/apps/cms_backend/routes/feed.py) describes the per-source and
  per-category limits.
- `web/openapi.json` and `web/src/api/schema.gen.ts` are regenerated with `pnpm api:generate` (a
  description change only).
- S18's status becomes `implemented`.

### Tests first

- [x] `test_feed_home_searcher.py`, with the in-memory fake, distinct `created_at` values and
  explicit categories:
  - [x] With enough variety: at most 2 per source and 2 per category, 10 feeds, newest first.
  - [x] Category cap across sources: every source's newest feed is `POLITICS`, so only the 2
    newest of them are picked in step 1 and the other categories fill the rest.
  - [x] Every candidate is `POLITICS`: 2 in step 1, 8 in step 2, so the page still has 10.
  - [x] Only one source has feeds (12): the 10 newest.
  - [x] Fewer than 10 home feeds: all of them.
  - [x] `CMS` and `EL_PAIS` feeds never appear.
  - [x] Only the 15 newest feeds of each source are candidates. The planned case (a 16th, older
    feed is never picked) cannot fail: step 2 needs at most 8 more feeds, fewer than the 13 a
    source has left among its 15. The test checks instead that the use case searches each home
    source, newest first, with `limit=15`, through the fake's `searched_criteria`.
  - [x] No feeds give `[]`.
- [x] Adapt or remove the S08 tests that no longer hold. They built feeds with random categories,
  which the category limit makes flaky, so they now set them. The same applies to
  `test_home_feeds.py`, whose scraping test also checks at most 2 per category on the page.
  `test_openapi.py` checks the new description.

### Implementation

- [x] Rewrite `FeedHomeSearcher.execute` with the candidates and the two steps; remove the global
  search.
- [x] Update the `/feed/home` description, then run `pnpm api:generate` in `web/` (only the
  description changes in `openapi.json` and `schema.gen.ts`).
- [x] Set S18's status to `implemented`.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and the web quality gate, and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Every phase is implemented. After review, commit phase 2 and open a pull request from
`feat/s18-varied-categories` to `main`.
