# I02 · Scraper robustness

**Status:** draft · **Fidelity:** intentional break with the ported behavior. Depends on S06, S07
and I01. Resolves improvements #3, #6, #8 and #9 from `README.md`.

## Goal
Make scraping store clean, non-repeated headlines and never hang: descriptions are decoded with the
page's real charset and are `null` when absent, El Mundo keeps the last character of its
descriptions, a slow site times out instead of blocking `/feed/home`, and the same headline is not
stored twice on the same day.

## Changes

### Missing description → `null` (#9)
- A scraped article whose description selector matches nothing, or whose trimmed text is empty, is
  stored with `description: null` (it was `""`).
- The rule applies after any per-source cleanup: an El Mundo kicker that is only `"."` becomes `null`.
- Feeds created through the API are unchanged: `PUT`/`PATCH` still accept `""`.

### Remove the id-regeneration loop (#6)
- A scraped feed is saved with the random UUID it was created with. The scraper no longer looks up
  that id before saving.
- A UUID4 collision is not handled (probability is negligible); it would overwrite the stored feed.

### Charset, El Mundo trimming, timeout and User-Agent (#8)
- **Charset:** each page is decoded with the charset it declares: the `charset` of the response
  `Content-Type` header, else the `<meta>` charset of the document, else UTF-8. An unknown charset
  label is treated as absent. No scraper has a fixed encoding any more (El Mundo currently declares
  `iso-8859-15`, not `iso-8859-1`).
- **El Mundo trimming:** after trimming whitespace, **one trailing period** is removed from the
  description (kickers read like `"Crucigrama."`). Any other last character is kept:
  `"¿Qué pasa?"` stays `"¿Qué pasa?"`, `"Sudoku..."` becomes `"Sudoku.."`.
- **Timeout:** every scraping request has a 10-second timeout (connect, read, write and pool). A
  timed-out source fails like any other failing scraper: its feeds are dropped, the failure is
  logged, the other sources are saved. `/feed/home` and `/feed/scrap` therefore never wait more than
  about 10 s per source.
- **Headers:** requests send `User-Agent: daily-trends-py`. The meaningless request header
  `Content-Type: text/html; charset=UTF-8` is no longer sent.
- Redirects are still followed; a non-2xx response is still parsed like any other page.

### Deduplicate by source + title + day (#3)
- A scraped feed is **not saved** when a feed with the same `source` and the same `title` (exact,
  case-sensitive, after trimming) already exists whose `createdAt` falls on the same **UTC day** as
  the scraped feed's `createdAt`.
- The same rule applies within one run: if a page lists the same headline twice, only the first is
  saved.
- Skipped feeds are not part of the `/feed/scrap` response (I01): it lists only the feeds saved by
  this run.
- Feeds of other sources never count (a `CMS` feed with the same title does not block a scraped one).
- The 5-per-source limit (S06) still counts extracted articles, before deduplication: a second run on
  the same day may save fewer than 5 feeds per source, or none.
- The day is UTC because `createdAt` is stored as `…Z`; a business timezone is #18.

## Unchanged
- Selectors, the `article` walk, skipping articles without author or title, the 5-per-source limit,
  parallel scrapers, a failing scraper being dropped, save errors propagating as 500 without rollback.
- `/feed/home` triggering rules (S07) and its response.
- Everything in `README.md` outside #3, #6, #8 and #9. In particular, concurrent runs may still store
  the same headline twice (#17): there is no unique index.

## Edge cases
- A second `/feed/scrap` on the same UTC day with unchanged front pages → 200 `[]`, nothing saved.
- A headline stored yesterday (UTC) and still on the front page today → saved again today.
- A stored feed whose `createdAt` is not in the `…Z` format written by this API (for example inserted
  directly in Mongo with an offset) may not be recognized as same-day (dates are text, #12).
- The response declares a charset but the `<meta>` declares another → the header wins.
- No charset in the header or the document → UTF-8.

## Acceptance criteria
- Front-page tests with hand-written HTML fixtures: a page declaring `iso-8859-15` in the header and
  one declaring it only in `<meta>` decode `€` correctly; no declaration decodes UTF-8; requests send
  the User-Agent and no `Content-Type`.
- El Mundo tests: a trailing period is removed, `?` is kept, an empty or `"."` kicker gives `null`.
- Extraction test: a missing or blank description gives `null` for every source.
- A timed-out request makes that scraper fail (the transport raises a timeout); the use case already
  drops it.
- Use-case tests: the id is not looked up before saving; a same-day duplicate (stored or within the
  run) is skipped and not returned; a duplicate from a previous UTC day or another source is saved.
- Repository integration test against real Mongo for the new same-day headline lookup.
- `scrap-feed.feature`: a second `/feed/scrap` answers an empty array and `/feed/list` stays at 12.
- The live smoke tests (marker `network`) still pass: 5 feeds per source on a first run.
- `docs/openapi.yml` describes deduplication and the nullable scraped description on `/feed/scrap`.
