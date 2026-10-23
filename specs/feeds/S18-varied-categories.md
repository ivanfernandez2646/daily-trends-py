# S18 · Varied categories

**Status:** draft · **Fidelity:** changes which scraped feeds are stored and which ones the front page
shows; no route, field or schema changes. Depends on S06, S08, S09, I02 and S10.

## Goal
Show news of every kind, not only politics. Each scraper keeps the first 5 articles of its front
page, and Spanish front pages open with national politics: on 2026-10-23, 4 of the 5 sources gave 3
to 5 `POLITICS` feeds out of their first 5, while sports, culture, technology and the rest sat lower
on the same pages (between 18 and 252 usable articles per page). Deduplication then keeps the
scheduled runs from adding anything new until the opening changes, and the front page picks the
2 newest feeds of each source from those batches.

This spec takes more articles from the page that is already downloaded, spread across categories,
and makes the front page mix categories too. It adds no requests, sources, categories or settings.

## Scraping: a varied selection per source
Replaces the "at most 5 per source" rule of S06 and S08.

- A scraper extracts every usable article of its front page with the existing rules (S06, I02,
  S08, S09): author, title and link required, category from the link.
- It then selects up to **15** feeds, at most **2 per category**, in rounds:
  1. walking the page in order, the first article of each category;
  2. if fewer than 15 were selected, walking it again, the second article of each category;
  3. it stops when it has 15 or the rounds run out.
- `OTHER` is a category like any other: at most 2 per source.
- The selected feeds keep the order of the page.
- A run stores at most **75** feeds (5 sources × 15). Deduplication by source + title + day (I02) is
  unchanged and applies after the selection: an already stored headline is skipped, not replaced by
  the next article of its category.
- The values 15 and 2 are constants of the scraping infrastructure, like the 5-per-source limit was.

## Front page (`GET /feed/home`): mix categories
Replaces the selection of S08. A scraping run gives every feed of a source the same `createdAt`, so
"its 2 newest feeds" are an arbitrary pair of the batch, usually its opening political stories.

- **Candidates:** the **15** newest feeds of each home source (S08), roughly its latest batch.
- **Selection**, walking all the candidates newest first:
  1. pick a feed when fewer than **2** feeds of its source and fewer than **2** feeds of its category
     are already picked, until there are **10**;
  2. if fewer than 10 were picked, walk them again and pick any feed not yet picked, until there are
     10.
- The result is at most 10 feeds, ordered by `createdAt` descending. Feeds with the same `createdAt`
  still have no guaranteed order among themselves.
- `CMS` and `EL_PAIS` feeds never appear, and no results → `[]` (unchanged).
- 15, 2, 2 and 10 are constants of the home use case.

## Category tables
Additions to the S09 tables, from sections that came out as `OTHER` on the front pages of
2026-10-23:

| Source | Section | Category |
|---|---|---|
| El Mundo | `pais-vasco`, `aragon` | `SOCIETY` |
| El Mundo | `la-lectura` | `CULTURE` |
| El Español | `el-cultural` | `CULTURE` |
| El Confidencial | `television` | `CULTURE` |
| El Confidencial | `inmobiliario` | `ECONOMY` |
| La Razón | `television` | `CULTURE` |
| La Razón | `tecnologia-consumo` | `TECHNOLOGY` |

- Stored feeds are not reclassified (S09).

## Unchanged
- Every route, request and response, the `FeedCategory` values, the stored documents and the indexes.
  No migration.
- The sources, selectors, timeout and decoding (S06, S08, I02), the schedule and single-flight guard
  (S10), deduplication (I02), the browse list (S12) and the web app (S14).

## Out of scope
- Scraping section pages (`/deportes`, `/cultura`…): more volume, but more requests, memory and
  selectors to maintain, and a different deduplication.
- New categories (lifestyle, gossip, travel), filtering out shopping sections, and recategorizing
  stored feeds.

## Edge cases
- A page whose usable articles are all `POLITICS` → 2 feeds from that source.
- A page with 3 categories of 5 articles each → 6 feeds: the first two of each.
- El Mundo, with 18 usable articles in 8 categories on 2026-10-23 (with this spec's tables) → 13
  feeds: 8 in the first round, 5 in the second. La Vanguardia, with 110 articles in 8 categories → 15.
- The first `POLITICS` article of a source was stored in an earlier run today → this run skips it and
  stores the second one, if it was selected; it does not reach for a third.
- Only one source has stored feeds → the front page shows up to 10 of them: 2 in step 1, the rest in
  step 2.
- Every candidate is `POLITICS` → 2 in step 1, 8 more in step 2: the page is never shorter because of
  the category limit.

## Acceptance criteria
- Front-page extraction tests with HTML fixtures:
  - the first round takes the first article of each category in page order, the second round the
    second one;
  - at most 2 per category, `OTHER` included;
  - at most 15 per source;
  - the selected feeds keep the page order;
  - articles without author, title or a usable link are skipped before the selection.
- One test per changed scraper that its table maps the new sections.
- Use-case tests for the home search with the in-memory fake:
  - at most 2 per source and 2 per category when there is enough variety, ordered by `createdAt`
    descending;
  - step 2 fills up to 10 when there is not;
  - `CMS` and `EL_PAIS` feeds never appear;
  - only the 15 newest feeds of each source are candidates.
- Repository integration test against real Mongo, if the home search needs a new query.
- `scrap-feed.feature` and `home-feed.feature` updated to the counts their fixtures now give; the
  second `/feed/scrap` still answers `[]`.
- The OpenAPI description of `/feed/home` describes the per-source and per-category limits, and
  `pnpm api:generate` is run so `web/openapi.json` and `schema.gen.ts` stay in sync.
- `S00` adds S18 to its table and updates the front-page glossary entry; `S08` and `S09` get a
  "See S18" note on the scraping limit, the front-page selection and the category tables.
