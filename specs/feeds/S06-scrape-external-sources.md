# S06 · Scrape external sources

**Status:** draft · **Fidelity:** exact (including the defects in `improvements/`), except for the
source replacement described in "Deliberate divergences". Depends on S02.

## `GET /feed/scrap`
- Runs **both** scrapers in parallel; if one fails its result is dropped without error and the others are saved. Response 200, empty body.

> **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** the response is 200 with the array of feeds saved by this run.

- Each scraper downloads the front page, walks the `article` elements in order and extracts author, title and description (trimmed text).
  - Skip an article with no author or no title.
  - Maximum **5 per source**.
  - Each article creates a new feed: random UUID, `source` per scraper, `createdAt` now, `updatedAt` `null`. The description is the text (can be `""`, not `null`).

> **Superseded by [I02](../improvements/I02-scraper-robustness.md):** a missing or blank description is stored as `null`.

- Every feed is saved. No content deduplication: each run inserts 5+5 new feeds even for the same headlines.
- If the id already existed it would be regenerated until free (never happens in practice).

> **Superseded by [I02](../improvements/I02-scraper-robustness.md):** the id is not looked up; each feed is saved with the id it was created with.

- A save error propagates as 500; feeds already saved are not rolled back.

## Selectors
| Source | URL | Author | Title | Description | Encoding |
|---|---|---|---|---|---|
| El Mundo (`EL_MUNDO`) | `https://elmundo.es/` | `.ue-c-cover-content__byline-name .ue-c-cover-content__link` | `.ue-c-cover-content__headline` | `.ue-c-cover-content__kicker` | **always iso-8859-1** |
| El Español (`EL_ESPANOL`) | `https://www.elespanol.com/` | `.art__author` | `.art__title` | `.art__subtitle` | response as text (UTF-8) |

- El Mundo: its description has its **last character removed** (if not `null`).
- No timeout; no specific headers beyond `Content-Type: text/html; charset=UTF-8` on the request.
- Redirects are followed (`https://elmundo.es/` answers 301 to `https://www.elmundo.es/`).
- A non-2xx response is not an error: its body is parsed like any other page, so it usually yields no feeds.

## Deliberate divergences from the original
- **El Español replaces El País.** Since 2026-10 `https://elpais.com/` answers 403 with a DataDome
  bot-protection page ("Please enable JS and disable any ad blocker") to any non-browser client,
  whatever the User-Agent. The original scraper parses that page, finds no `article` and silently
  saves nothing from El País. The port's goal is a working Python application, not fidelity to a
  given newspaper, so the El País scraper is not ported and an El Español scraper (new source
  `EL_ESPANOL`) runs in its place. Bypassing the bot protection was rejected.
  - `FeedSource.EL_PAIS` stays valid: feeds already stored and the ported `.feature` files use it.
  - Only the source changes: the El Español scraper follows the same rules as every scraper
    (`article`, trimmed text, skip, limit 5, `""` description, UTF-8 like the original El País).
  - To restore El País, add its scraper back (row: `https://elpais.com/`, `.c_a`, `.c_h`, `.c_d`,
    response as text) once it is reachable again.

## Edge cases
- Scrapers return nothing (HTML changed or the site blocks the request): nothing is saved, response still 200.

## Acceptance criteria
- Behavior tests use hand-written HTML fixtures, never the real network: extraction, limit 5, skipping, El Mundo trimming and iso-8859-1.
- One live smoke test per scraper against the real front page (marker `network`, part of the quality gate): 5 feeds with the scraper's source, non-empty author and title. It detects markup or charset changes that fixtures cannot.
- One scraper fails, the other saves.
- Cover the `scrap` `.feature` file (2 CMS → after scraping home=10, list=12). The `/feed/home` steps wait for S07; until then the scenario checks list=2 → scrap → list=12.
