# S06 · Scrape external sources

**Status:** draft · **Fidelity:** exact (including the defects in `improvements/`). Depends on S02.

## `GET /feed/scrap`
- Runs **both** scrapers in parallel; if one fails its result is dropped without error and the others are saved. Response 200, empty body.
- Each scraper downloads the front page, walks the `article` elements in order and extracts author, title and description (trimmed text).
  - Skip an article with no author or no title.
  - Maximum **5 per source**.
  - Each article creates a new feed: random UUID, `source` per scraper, `createdAt` now, `updatedAt` `null`. The description is the text (can be `""`, not `null`).
- Every feed is saved. No content deduplication: each run inserts 5+5 new feeds even for the same headlines.
- If the id already existed it would be regenerated until free (never happens in practice).
- A save error propagates as 500; feeds already saved are not rolled back.

## Selectors
| Source | URL | Author | Title | Description | Encoding |
|---|---|---|---|---|---|
| El País (`EL_PAIS`) | `https://elpais.com/` | `.c_a` | `.c_h` | `.c_d` | response as text |
| El Mundo (`EL_MUNDO`) | `https://elmundo.es/` | `.ue-c-cover-content__byline-name .ue-c-cover-content__link` | `.ue-c-cover-content__headline` | `.ue-c-cover-content__kicker` | **always iso-8859-1** |

- El Mundo: its description has its **last character removed** (if not `null`).
- No timeout; no specific headers beyond `Content-Type: text/html; charset=UTF-8` on the request.

## Edge cases
- Scrapers return nothing (HTML changed): nothing is saved, response still 200.

## Acceptance criteria
- Tests use recorded HTML fixtures, never the real network: extraction, limit 5, skipping, El Mundo trimming and iso-8859-1.
- One scraper fails, the other saves.
- Cover the `scrap` `.feature` file (2 CMS → after scraping home=10, list=12).
