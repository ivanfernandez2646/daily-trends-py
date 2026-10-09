# S07 · Front page

**Status:** draft · **Fidelity:** exact. Depends on S03 (criteria) and S06 (scraping).

## `GET /feed/home`
1. Search with filter `source = EL_MUNDO OR source = EL_ESPANOL`, sort `createdAt` desc, `limit 10`. (`EL_ESPANOL` replaces `EL_PAIS`, as it replaces El País as a scraped source, see S06. The database starts empty, so there are no stored `EL_PAIS` feeds to show; the `EL_PAIS` source stays valid for other routes.)
2. If there are results and the **newest** is from a day before today (day-level comparison, server local time) → run the scraping from S06 **inside the request** and repeat the search.
3. If there are no results, scraping is **not** triggered (returns `[]`).
4. Response 200 with the array. Never includes `CMS` feeds.

> **Superseded by [I03](../improvements/I03-background-front-page-scraping.md):** a stale page requests one scraping run in the background and the response is the first search, without waiting or searching again.

- If scraping fails with a propagated error, the response is 500 (only 400 is mapped for this route).

> **Superseded by [I03](../improvements/I03-background-front-page-scraping.md):** errors of the background run are logged and never reach the response.

> **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** no error is mapped to 400 on this route; an invalid stored feed answers 500.

- Ordering is textual over the stored ISO `createdAt` strings (S03).
- In the acceptance harness, a feed whose `createdAt` cell is empty or missing is created with the current time, as the original harness does. That is why the EL_MUNDO feed with an empty `createdAt` in the `home` `.feature` sorts first, and why that scenario does not trigger scraping.

## Edge cases
- If both scrapers fail, the retry repeats on every request while the newest feed is from a previous day.
- Scrapers return nothing: the front page is still returned with what existed.

## Acceptance criteria
- Tests with a fixed clock: newest is today (no scraping), newest is older (scraping + re-search), empty (no scraping).
- Cover the `home` `.feature` file (external only; empty → `[]`). Its `EL_PAIS` row becomes `EL_ESPANOL`.
