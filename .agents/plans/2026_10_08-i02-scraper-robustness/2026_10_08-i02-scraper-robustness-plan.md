---
name: 'i02-scraper-robustness'
description: 'Scraped descriptions are null when absent, the id-regeneration loop is gone, pages are decoded with their declared charset under a timeout and User-Agent, El Mundo strips only a trailing period, and the same headline is not stored twice on the same UTC day'
spec: 'specs/improvements/I02-scraper-robustness.md'
branch: 'fix/i02-scraper-robustness'
created_at: '2026-10-08T11:44:26Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
implemented_at: '2026-10-08T11:45:56Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I02 · Scraper robustness

## Goal

Resolve improvements #3, #6, #8 and #9. Scraped feeds store `null` for a missing description. They
keep the id they were created with. Pages are decoded with their declared charset, with a 10 s
timeout and a `daily-trends-py` User-Agent. El Mundo removes only a trailing period. A headline
already stored for the same source on the same UTC day is skipped. The repository stays green after
each phase.

## Context

- Branch `fix/i02-scraper-robustness` is cut from `fix/i01-http-contract-fixes`. I01 is not merged
  into `main` yet, and I02 builds on `FeedScraper.execute()` returning the saved feeds.
- Scraping lives in `contexts/cms/feeds/infrastructure/scrap/`:
  - `front_page.py`: `ScrapMapping` (with a fixed `encoding`), `scrap_front_page` (GET with a
    `Content-Type` header, `response.content.decode(mapping.encoding)`) and `extract_feeds`
    (`FeedDescription(_text(...))`, so `""` when missing).
  - `el_mundo_feed_scraper.py`: `encoding="iso-8859-1"`; `_without_last_description_character`.
  - `el_espanol_feed_scraper.py`: `encoding="utf-8"`.
- `application/scrap/feed_scraper.py`: `FeedScraper.execute()` loops `repository.find(feed.id)` to
  regenerate ids, then saves each feed.
- `apps/cms_backend/main.py` builds `httpx.AsyncClient(transport=http_transport, timeout=None,
  follow_redirects=True)` with a comment pointing at #8.
- `FeedRepository` port: `save`, `find`, `delete`, `search(criteria)`. `Criteria` only expresses
  OR-equality filters, so the same-day lookup needs a dedicated port method.
- `createdAt` is written as `YYYY-MM-DDTHH:MM:SS.mmmZ` (`DateTimeValueObject.now`), so a UTC-day
  range is a text range `[YYYY-MM-DD, next day)` in Mongo.
- Fakes: `tests/contexts/cms/feeds/fakes/{in_memory_feed_repository,failing_feed_repository,stub_feed_scrap}.py`.
  Fixtures: `tests/fixtures/scrap/*.html` served by `tests/scrap_fixtures.py` through
  `create_app(..., http_transport=...)`.
- Live smoke tests (marker `network`) call each scraper directly and are unaffected by deduplication.
- `specs/feeds/S06-scrape-external-sources.md` gets a one-line "Superseded by I02" note next to each
  section a phase changes.

## Phase 1: Null descriptions and no id-regeneration loop (#9, #6)

The smallest behavior changes: extraction and the use case, with no new contract on the port.

### Public contracts

- Scraped feeds: `description` is `null` when the selector matches nothing or its trimmed text is
  `""`. For El Mundo, after the existing last-character removal, an empty result is also `null`.
- `FeedScraper.execute()` saves each scraped feed with its own id and never calls
  `repository.find`.

### Tests first

- [x] `test_front_page.py` (extraction): an article without a description element and one with a
      blank description produce `FeedDescription(None)`.
- [x] `test_el_mundo_feed_scraper.py`: the fixture article without a kicker now gives `null`
      (a kicker emptied by trimming maps to `null` too; Phase 2 tests `"."` explicitly).
- [x] `test_feed_scraper.py`: replace `test_regenerates_and_returns_the_id_...` with
      `test_saves_each_feed_with_its_own_id_without_looking_it_up` (asserts `searched_ids == []` and
      the saved id is the scraped one).
- [x] `test_el_espanol_feed_scraper.py`: fixture and live smoke test expect `null`, never `""`.

### Implementation

- [x] `extract_feeds`: `FeedDescription(_text(...) or None)`.
- [x] El Mundo: map an empty trimmed description to `FeedDescription(None)`.
- [x] `FeedScraper.execute`: remove the `while ... find` loop and the `dataclasses`/`FeedId` imports.
- [x] S06: "Superseded by I02" notes on the `""` description and the id regeneration.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggested commits:
  - `fix(i02): store a null description for scraped articles without one`
  - `refactor(i02): drop the scraped feed id-regeneration loop`
  - `fix(i02): normalize empty scraped descriptions and save scraped ids as created`

## Phase 2: Declared charset, El Mundo trimming, timeout and User-Agent (#8)

Everything about how a front page is fetched and decoded, contained in infrastructure and the
composition root.

### Public contracts

- `ScrapMapping` loses `encoding`.
- `scrap_front_page(client, mapping)`: GET without a `Content-Type` header. The bytes are decoded
  with the `Content-Type` header charset (`response.charset_encoding`) when it is a known codec,
  else the document's `<meta>` charset, else UTF-8 (BeautifulSoup on bytes with `from_encoding`, or
  equivalent, decided in TDD).
- El Mundo: `_without_trailing_period`. Strip one trailing `.`; an empty result gives `null`.
- Composition root: `httpx.AsyncClient(transport=..., timeout=SCRAP_TIMEOUT_SECONDS (10.0),
  headers={"User-Agent": "daily-trends-py"}, follow_redirects=True)`. These are constants in
  `main.py`, and the #8 comment is removed.
- `docs/openapi.yml`: no change in this phase.

### Tests first

- [ ] `test_front_page.py`:
  - header `text/html; charset=iso-8859-15` and bytes encoded in iso-8859-15 decode `€`;
  - no header charset, `<meta charset="iso-8859-15">` decodes `€`;
  - neither → UTF-8 (`ñ` from UTF-8 bytes);
  - header and meta disagree → header wins;
  - unknown header charset → falls back to meta/UTF-8.
- [ ] `test_el_mundo_feed_scraper.py` / `test_el_espanol_feed_scraper.py`: replace the `Content-Type`
      request assertion with "no `Content-Type` header". The El Mundo fixture test now relies on the
      declared charset. Update `tests/fixtures/scrap/el_mundo.html` and its transport to declare
      `iso-8859-15` like the live site, if they don't already.
- [ ] El Mundo trimming: `"Crucigrama."` → `"Crucigrama"`, `"¿Qué pasa?"` kept, `"Sudoku..."` →
      `"Sudoku.."`, `"."` → `null`.
- [ ] A transport that raises `httpx.ReadTimeout` makes `scrap()` raise. The use-case drop is already
      covered by `test_drops_a_failing_scraper_...`.
- [ ] App-level test (in `test_scrap_feeds.py`): requests reaching the transport carry
      `User-Agent: daily-trends-py`. A transport that times out for one source still answers 200
      with the other source's feeds.

### Implementation

- [ ] Remove `encoding` from `ScrapMapping` and both mappings. Decode by declared charset in
      `scrap_front_page`.
- [ ] Replace `_without_last_description_character` with `_without_trailing_period`.
- [ ] Configure the timeout and User-Agent in `main.py`.
- [ ] S06: "Superseded by I02" notes on the encoding column/row, the trimming rule and
      "No timeout; no specific headers".
- [ ] Run the quality gate from `AGENTS.md`, including the `network` smoke tests, and fix failures.
- [ ] STOP for user review. Suggested commits:
  - `fix(i02): decode front pages with their declared charset`
  - `fix(i02): strip only a trailing period from El Mundo descriptions`
  - `fix(i02): time out scraping requests and identify them with a User-Agent`

## Phase 3: Deduplicate by source + title + UTC day (#3)

A new port method, its Mongo implementation and the use-case rule, verified end to end.

### Public contracts

- `FeedRepository.exists_headline(source: FeedSource, title: FeedTitle, day: date) -> bool`:
  `True` when a feed with that source and exact title has a `createdAt` in that UTC day.
- `MongoFeedRepository.exists_headline`: `find_one({"source": ..., "title": ...,
  "createdAt": {"$gte": "YYYY-MM-DD", "$lt": "<next day>"}})` (text range, see #12).
- `InMemoryFeedRepository` / `FailingFeedRepository` fakes implement it.
- `FeedScraper.execute()`: skips a feed when `exists_headline(...)` is true or when its
  `(source, title, day)` was already saved in this run. Skipped feeds are not returned.
- `GET /feed/scrap`: a second run on the same UTC day with unchanged pages → `200 []`.
- `docs/openapi.yml` `/feed/scrap`: describes deduplication and the nullable `description`.

### Tests first

- [ ] `test_feed_scraper.py`:
  - a feed whose headline exists on the same UTC day is not saved nor returned;
  - two identical headlines in one run → only the first saved;
  - the same title from another source, or stored on a previous UTC day, is saved.
- [ ] `test_mongo_feed_repository.py` (integration): `exists_headline` is true for same source, title
      and day. It is false for another source, another title, the previous day, and the next day at
      `00:00:00.000Z`.
- [ ] `features/scrap-feed.feature`: after the existing steps, a second `/feed/scrap` answers an
      array of length 0 and `/feed/list` stays at 12.

### Implementation

- [ ] Add `exists_headline` to the port, the Mongo repository and the fakes.
- [ ] `FeedScraper`: derive the UTC day from `feed.created_at` and track the run's seen headlines.
- [ ] `docs/openapi.yml` and an S06 "Superseded by I02" note on "No content deduplication".
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggested commits:
  - `fix(i02): skip scraped headlines already stored the same UTC day`
  - `feat(i02): add a same-day headline lookup to the feed repository`
  - `fix(i02): deduplicate scraped feeds by source, title and day`

## Next step

Review Phase 1, then run `/ai-project-implement-phase` for Phase 2.
