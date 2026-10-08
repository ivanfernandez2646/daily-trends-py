---
name: 's06-scrape-external-sources'
description: 'GET /feed/scrap scrapes El Mundo and El Español front pages in parallel and saves up to 5 feeds per source'
spec: 'specs/feeds/S06-scrape-external-sources.md'
branch: 'feat/s06-scrape-external-sources'
created_at: '2026-10-08T10:11:04Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
implemented_at: '2026-10-08T10:24:27Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S06 · Scrape external sources

## Goal

`GET /feed/scrap` runs the El Mundo and El Español scrapers in parallel, drops a scraper that fails,
and saves up to 5 new feeds per source. It answers 200 with an empty body, or 500 when a save fails.
The behavior and its defects match the Node reference, except that El Español replaces El País (see
the spec's "Deliberate divergences"). Fixtures cover the behavior offline, and one live smoke test
per scraper checks the real front pages. The repository stays green after each phase.

## Context

S02 delivered `Feed.create` (it records `feed.created`), the value objects, `FeedRepository.find` and
`save`, `run_controller`, and the pytest-bdd steps in `tests/apps/cms_backend/conftest.py`. The
`routes/__init__.py` docstring already says that `/feed/scrap` must come before `/feed/{id}`. `httpx`,
`beautifulsoup4` and `lxml` are already runtime dependencies, but nothing imports them yet.
`create_app(settings)` has no seam for the network yet.

Behavior is ported from the following files under `reference/daily-trends-node/`:

- `src/contexts/cms/feeds/domain/FeedScrap.ts` and `FeedScraperDomainService.ts`
- `src/contexts/cms/feeds/application/scrap/FeedScraper.ts`
- `src/contexts/cms/feeds/infrastructure/scrap/{FeedScraperBase,ElPaisFeedScraper,ElMundoFeedScraper}.ts`
- `src/apps/cms/backend/controllers/feeds/FeedScraperController.ts`
- `dependency-injection/apps/feed.yaml`
- `scrap-feed.feature`, `FeedScraper.test.ts` and `FeedScraperDomainService.test.ts`

### Findings against the real sites (2026-10-08)

- **`https://elpais.com/` answers 403** with a DataDome bot-protection page to every non-browser
  client, whatever the User-Agent (httpx default, `node`, `Mozilla/5.0`). The reference parses that
  page and saves nothing, without any error.
- **`https://elmundo.es/` answers 301** to `https://www.elmundo.es/`, which serves `iso-8859-15` with
  59 `article`s. The reference selectors give 5 feeds. The kicker ends in "." (`Tribunales.`), which
  explains the last-character trim.
- **`https://www.elespanol.com/` answers 200** in UTF-8. With `.art__author`, `.art__title` and
  `.art__subtitle`, the reference algorithm gives 5 feeds, skipping 1 article on the way, and most
  descriptions are `""`.
- **Other candidates:**
  - La Razón and 20minutos also work, but their authors are noisier.
  - El Confidencial, El Periódico and EFE block the request.

### Agreed decisions

- **Granularity:** intermediate, 2 phases.
- **El Español replaces El País.** The El País scraper is not ported. `FeedSource` gains
  `EL_ESPANOL`, and `EL_PAIS` stays because stored feeds and verbatim features use it. The reason is
  recorded in S06, S00, S02, S07, the README and `docs/openapi.yml`. Bypassing the bot protection was
  rejected.
- **`scrap-feed.feature` without `/feed/home`.** S07 owns `/feed/home`. S06 ports the scenario as
  list=2 → scrap → list=12, and S07 restores the two home checks verbatim.
- **Network seam:** `create_app(settings, http_transport=None)`. Acceptance tests pass an
  `httpx.MockTransport` that serves the fixtures, so the real scrapers run end to end.
- **Fixtures:** small hand-written HTML that mimics the real markup. The El Mundo fixture is stored as
  iso-8859-1 bytes.
- **Live smoke tests:** one per scraper adapter, marked `network`. They run in the normal gate
  (`uv run pytest`, CI) and are not deselected by default. There is no live end-to-end test.

### Smaller decisions

- **No domain service.** `FeedScraper` runs the scrapers itself with `asyncio.gather(...,
  return_exceptions=True)`.
  - A failed scraper is dropped and logged as a warning. This is not observable over HTTP.
  - Scraper order is El Mundo first, as in the reference DI, then El Español. Feeds are saved in that
    order.
- **No events are published.** `Feed.create` records `feed.created`, but `FeedScraper` takes no event
  bus and never pulls the events, as in the reference.
- **The id-regeneration loop is kept** (improvement #6). While `repository.find(feed.id)` finds a
  feed, the feed is rebuilt with `FeedId.random()` and checked again. A save error propagates, and
  feeds already saved stay saved.
- **Text extraction follows cheerio's `.find(sel).text().trim()`.** The text of every match inside the
  `article` is joined, then `str.strip()` is applied.
  - An article is skipped when its author or title is empty.
  - Extraction stops at 5 feeds.
  - An empty description is stored as `""` (improvement #9 is out of scope).
- **Request:** one shared `httpx.AsyncClient(timeout=None, follow_redirects=True)` owned by the
  lifespan, with the `Content-Type: text/html; charset=UTF-8` header and no other custom headers.
  - There is no `raise_for_status`: like `fetch`, a non-2xx body is parsed.
  - A transport error, such as a failed connection, propagates, and `FeedScraper` drops that scraper.
- **Decoding:**
  - El Español decodes the body as UTF-8 with replacement and ignores any header charset, as
    `fetch().text()` does.
  - El Mundo always decodes iso-8859-1 (improvement #8).
- **Parsing:** `extract_feeds` runs in `asyncio.to_thread`, with bs4 and `lxml`, so the event loop is
  never blocked.
- **El Mundo trimming:** `description[:-1]` when the description is not `None`, so `""` stays `""`.
- **Response:** 200 with an empty body (improvement #11 is out of scope). Any error → 500
  `{"error": …}` through `run_controller` with no mappings.

## Phases

## Phase 1: Scrape El Español end to end

Add the scraping port, the `FeedScraper` use case, the shared extraction, the El Español adapter and
the `EL_ESPANOL` source. Add the network seam in the composition root and `GET /feed/scrap`, wired
with El Español only.

### Public contracts

- `FeedSource.EL_ESPANOL = "EL_ESPANOL"`.
- `daily_trends_py.contexts.cms.feeds.domain.feed_scrap`:
  `class FeedScrap(Protocol): async def scrap(self) -> list[Feed]: ...`
- `daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper`:
  `FeedScraper(repository: FeedRepository, scrapers: Sequence[FeedScrap])` with
  `async execute() -> None`.
- `daily_trends_py.contexts.cms.feeds.infrastructure.scrap.front_page`:
  - `@dataclass(frozen=True) class ScrapMapping`. Fields: `url: str`, `source: FeedSource`,
    `author_selector: str`, `title_selector: str`, `description_selector: str`.
  - `extract_feeds(html: str, mapping: ScrapMapping) -> list[Feed]`.
  - `async fetch_front_page(client: httpx.AsyncClient, url: str) -> bytes`. It sends the
    `Content-Type` header.
- `daily_trends_py.contexts.cms.feeds.infrastructure.scrap.el_espanol_feed_scraper`:
  `ElEspanolFeedScraper(client: httpx.AsyncClient)` implements `FeedScrap`. It uses
  `https://www.elespanol.com/`, `EL_ESPANOL`, `.art__author`, `.art__title` and `.art__subtitle`, and
  decodes as UTF-8.
- Composition root: `create_app(settings: Settings, http_transport: httpx.AsyncBaseTransport | None = None)`.
  - The lifespan creates `httpx.AsyncClient(transport=http_transport, timeout=None,
    follow_redirects=True)` and closes it on shutdown.
  - It sets `app.state.feed_scraper = FeedScraper(repo, [ElEspanolFeedScraper(client)])`.
- HTTP: `GET /feed/scrap` → 200 with an empty body; any error → 500 `{"error": …}`. It is declared in
  `routes/feed.py` above `GET /feed/{id}`.
- `pyproject.toml`: register the marker `network: hits real external websites`.
- Test support:
  - `tests/fixtures/scrap/el_espanol.html`.
  - `tests/scrap_fixtures.py` with `FrontPagesTransport(*, failing_hosts: Collection[str] = ())`, an
    `httpx.MockTransport`. It serves each fixture by host, answers 404 for unknown hosts, raises
    `httpx.ConnectError` for failing hosts, and records `requests`.
  - `tests/contexts/cms/feeds/fakes/failing_feed_repository.py` with
    `FailingFeedRepository(*, saves_before_failing: int, error: Exception)`.
  - In `tests/apps/cms_backend/conftest.py`, a `front_pages_transport` fixture that `app` uses. A test
    overrides it with `pytest.mark.parametrize`.
  - `tests/contexts/cms/feeds/fakes/stub_feed_scrap.py` with
    `StubFeedScrap(feeds: list[Feed] | None = None, error: Exception | None = None)`.
- Test suites:
  - `tests/contexts/cms/feeds/application/scrap/test_feed_scraper.py`
  - `tests/contexts/cms/feeds/infrastructure/scrap/test_front_page.py`
  - `tests/contexts/cms/feeds/infrastructure/scrap/test_el_espanol_feed_scraper.py` (fixture tests,
    plus one test marked `network`)
  - `tests/apps/cms_backend/test_scrap_feeds.py` (marked `integration`)

### Tests first

- [x] `FeedScraper` saves every feed from every scraper, in scraper order.
- [x] `FeedScraper` drops a scraper that raises and still saves the others' feeds.
- [x] `FeedScraper` saves nothing when the scrapers return nothing.
- [x] `FeedScraper` regenerates the id when it already exists and saves the feed with a new id and the
      same title, description, author and source.
- [x] `FeedScraper` propagates a save error, and feeds saved before the error stay saved.
- [x] `extract_feeds`:
  - [x] Returns trimmed author, title and description in document order, with a random UUID, the
        mapping's source, `createdAt` now and `updatedAt` `None`.
  - [x] Skips an article with no author or no title.
  - [x] Stops at 5 feeds.
  - [x] Stores a missing description as `""`.
  - [x] Joins the text of several matches.
- [x] `ElEspanolFeedScraper`, through the `MockTransport` fixture:
  - [x] Requests `https://www.elespanol.com/` with the `Content-Type` header.
  - [x] Returns 5 `EL_ESPANOL` feeds with accented UTF-8 text intact.
  - [x] Parses a non-2xx body without raising, so a blocked page gives `[]`.
- [x] `network`: the live `ElEspanolFeedScraper` returns 5 feeds. Each has source `EL_ESPANOL`, a
      non-empty author and title, and a string description.
- [x] `integration`:
  - [x] With 2 CMS feeds, `GET /feed/scrap` → 200 with an empty body, then `GET /feed/list` has 7
        feeds.
  - [x] When the scraper's host fails with a transport error, `GET /feed/scrap` → 200 and nothing is
        saved.

### Implementation

- [x] Check whether the real URLs redirect, and set `follow_redirects` on the client to match `fetch`
      (see the findings above).
- [x] Add `EL_ESPANOL`, `FeedScrap`, `FeedScraper`, `front_page.py` and `ElEspanolFeedScraper`.
- [x] Add `http_transport` to `create_app`, plus the client lifecycle and the `feed_scraper` wiring.
- [x] Add `GET /feed/scrap` above `GET /feed/{id}`.
- [x] Make the `app` fixture in `tests/apps/cms_backend/conftest.py` build the app with
      `FrontPagesTransport`.
- [x] Register the `network` marker.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms/feeds tests/apps/cms_backend
uv run pytest -m network
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Phase 2: Scrape El Mundo and port the feature

Add the El Mundo adapter with iso-8859-1 decoding and the last-character trim. Wire both scrapers,
El Mundo first, and port `scrap-feed.feature`.

### Public contracts

- `daily_trends_py.contexts.cms.feeds.infrastructure.scrap.el_mundo_feed_scraper`:
  `ElMundoFeedScraper(client: httpx.AsyncClient)` implements `FeedScrap`.
  - It uses `https://elmundo.es/` and `EL_MUNDO`.
  - Its selectors are `.ue-c-cover-content__byline-name .ue-c-cover-content__link`,
    `.ue-c-cover-content__headline` and `.ue-c-cover-content__kicker`.
  - It always decodes iso-8859-1 and removes the last character of each description.
- Composition root: `FeedScraper(repo, [ElMundoFeedScraper(client), ElEspanolFeedScraper(client)])`.
- Test support: `tests/fixtures/scrap/el_mundo.html` (iso-8859-1 bytes), served by
  `FrontPagesTransport`.
- Test suites:
  - `tests/apps/cms_backend/features/scrap-feed.feature`: the reference scenario without the two
    `/feed/home` checks. It runs list=2 → scrap (200, empty) → list=12.
  - `tests/apps/cms_backend/test_scrap_feeds.py`: `scenarios(...)` is added.
  - A new step `The response is an array with length {length:d}` in
    `tests/apps/cms_backend/conftest.py`.
  - `tests/contexts/cms/feeds/infrastructure/scrap/test_el_mundo_feed_scraper.py` (fixture tests,
    plus one test marked `network`).

### Tests first

- [ ] `ElMundoFeedScraper`, through the `MockTransport` fixture:
  - [ ] Requests `https://elmundo.es/`.
  - [ ] Decodes iso-8859-1, so accents and `ñ` are intact.
  - [ ] Returns 5 `EL_MUNDO` feeds, skipping articles with no author or title.
  - [ ] Removes the last character of each description, and `""` stays `""`.
- [ ] `network`: the live `ElMundoFeedScraper` returns 5 feeds. Each has source `EL_MUNDO`, a
      non-empty author and title, and no mojibake (`Ã`/`Â`) in any text.
- [ ] `integration`: `scrap-feed.feature` checks list=2, then scrap → 200 with an empty body, then
      list=12.
- [ ] `integration`: when El Mundo fails and El Español succeeds, `GET /feed/scrap` → 200 and list
      grows by 5.

### Implementation

- [ ] Add `ElMundoFeedScraper` and the `el_mundo.html` fixture.
- [ ] Wire both scrapers in `create_app`, El Mundo first.
- [ ] Add the array-length step and `scrap-feed.feature`.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

### Verification

```bash
uv run pytest tests/contexts/cms/feeds tests/apps/cms_backend
uv run pytest -m network
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

## Next step

Phase 1 is implemented and awaits review (and an optional `/ai-project-conventional-commit`). Then
run `/ai-project-implement-phase` for Phase 2.
