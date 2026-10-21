---
name: 's09-feed-category-and-url'
description: 'Every feed has a required category from a fixed list and the nullable URL of its original article; the list filters by category and scraped feeds take both from the article link'
spec: 'specs/feeds/S09-feed-category-and-url.md'
branch: 'feat/s09-feed-category-and-url'
created_at: '2026-10-20T15:38:43Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-21T10:00:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S09 · Feed category and article URL

## Goal

Every feed carries a `category` (`FeedCategory`, required) and a `url` (`FeedUrl`, nullable).
`PUT` requires the category and `PATCH` can change it. `GET /feed/list?category=` filters by
category. Scraped feeds store the article link and derive their category from it, and articles
without a usable link are skipped.

## Context

- `FeedSource` (`contexts/cms/feeds/domain/value_objects.py`) is a `StrEnum` whose `_missing_`
  raises `InvalidArgumentError`. `FeedCategory` copies that shape, so an unknown stored value
  becomes `InvalidStoredFeed` (500) through `_to_feed`'s existing `except InvalidArgumentError`.
- `FeedCriteria.FIELDS` comes from `Feed`'s init fields, so `category` becomes filterable as soon
  as it is a `Feed` field. `MongoRepository._by_criteria` turns `Filter("category", c)` into
  `{"$or": [{"category": "SPORTS"}]}`. The in-memory fake compares primitive values, so neither
  needs a change for the filter.
- `_to_document` is generic over `to_primitives()`. `_to_feed` lists its keys explicitly and must
  read `category` and `url`. Both keep their names in Mongo, so `_STORED_NAMES` stays as it is.
- Request schemas use `ConfigDict(strict=True)`, and unknown fields are ignored, so an extra `url`
  is dropped with no code. `UpdateFeedRequest` is a `TypedDict` splatted into
  `FeedUpdater.execute`, so `category: NotRequired[FeedCategory]` tells absent and `null` apart
  for free. **Risk:** strict Pydantic accepts only enum instances for Python input. If FastAPI
  validates the parsed body as Python, `"SPORTS"` is rejected. A schema test settles it; if
  needed, only `category` gets `Strict(False)`.
- `/feed/list` has no query parameters today, and test_openapi asserts it declares only 500. A
  `FeedCategory | None` query parameter gives a `RequestValidationError`, which becomes a 400
  `query.category: …` (`errors.py`). The app strips 422 from OpenAPI, and the test checks that
  stays true.
- **Agreed:** the domain does not enforce "scraped feeds have a URL". The migration gives existing
  scraped feeds `url: null`, and they must stay readable. The rule lives in the scraper.
- **Agreed:** the spec now adds the "closest link around the title" rule. El Confidencial and El
  Mundo wrap the headline in its link, and El Mundo's byline is also a link.
- Scraping: `scrape_front_page` already has `response.url` (the client follows redirects), but
  `extract_feeds(html, mapping, now)` does not receive it. Fixture hrefs are `/noticia-N.html`
  with no section segment.
- Migrations: append `m0002_feeds_category_and_url` to `MIGRATIONS`. Use plain strings with no
  domain imports, `update_many` with `$exists: false` filters, and named indexes (see the
  `ai-project-mongo-migrations` skill).

## Phases

## Phase 1: Category and URL on every feed

Feeds gain both fields end to end: domain, use cases, `PUT`/`PATCH`, every response, Mongo and the
migration. Until Phase 3, scrapers create feeds with `FeedCategory.OTHER` and `FeedUrl(None)`.
That is a deliberate interim state that keeps the suite green.

### Public contracts

- `FeedCategory(StrEnum)`: `POLITICS, INTERNATIONAL, ECONOMY, SOCIETY, SPORTS, CULTURE,
  TECHNOLOGY, SCIENCE, HEALTH, OPINION, OTHER`. `_missing_` raises
  `InvalidArgumentError("<FeedCategory> does not allow the value <x>")`.
- `FeedUrl` is a `@dataclass(frozen=True)` value object.
  - Its `value: str | None`.
  - It accepts an absolute `http`/`https` URL with a host, or `None`.
  - Anything else (relative, another scheme, blank, a non-string) raises `InvalidArgumentError`.
- `Feed` gains the fields `category: FeedCategory` and `url: FeedUrl`.
  - `Feed.create(*, id, title, description, author, source, category, url, now)`.
  - `Feed.update(*, now, title=None, description=None, category=None) -> Feed | None`. A
    different category sets `updated_at`; the same one is no change. `url` is never updated.
  - `FeedPrimitives` gains `category: FeedCategory` and `url: str | None`.
- `FeedCreator.execute(*, id, title, description, author, source, category: FeedCategory) ->
  Feed`. It stores `FeedUrl(None)`.
- `FeedChanges` gains `category: FeedCategory`.
- HTTP request bodies:
  - `CreateFeedRequest.category: FeedCategory`, required.
  - `UpdateFeedRequest.category: NotRequired[FeedCategory]`.
  - Missing, `null`, non-string or unknown values give a 400 in the usual `{"error": …}` format.
- `FeedResponse` field order: `id, title, description, author, source, category, url,
  created_at, updated_at`. `url` is nullable.
- OpenAPI:
  - a `FeedCategory` enum schema with the 11 values;
  - `category` required in `CreateFeedRequest` and optional in `UpdateFeedRequest`;
  - `url` nullable on `FeedResponse`.
- Mongo:
  - Documents store `category` (string) and `url` (string or null).
  - Migration `m0002_feeds_category_and_url`:
    - sets `category: "OTHER"` where it is missing;
    - sets `url: null` where it is missing;
    - creates the index `category_created_at_desc` on `category: 1, createdAt: -1`.
- Test harness:
  - `There are feeds:` gains a required `category` column and an optional `url` column. An empty
    `url` means `null`.
  - `FeedMother.random(category=, url=)`.
  - New `FeedCategoryMother` and `FeedUrlMother`.
  - `FeedDocumentMother` stores both fields.

### Tests first

- [x] `test_feed_value_objects.py`:
  - `FeedCategory` parses each of the 11 values;
  - `FeedCategory` rejects unknown, lowercase (`sports`) and `None` values;
  - `FeedUrl` accepts `http`, `https` (query and fragment kept) and `None`;
  - `FeedUrl` rejects relative, `ftp:`, blank and scheme-only values.
- [x] `test_feed.py`:
  - `create` keeps the category and the URL, and `FeedCreatedDomainEvent` is unchanged;
  - `update` with a new category sets `updated_at`;
  - the same category returns `None`;
  - the category combines with a title change;
  - the URL is kept on update;
  - primitives round-trip.
- [x] `test_feed_creator.py`: the created feed has the given category and `url` `None`.
- [x] `test_feed_updater.py`:
  - `category` changes the feed and is saved;
  - the same category saves nothing;
  - absent keeps it.
- [x] `test_feed_schemas.py`:
  - create requires `category`, and accepts `"SPORTS"` from JSON (the strict-mode check);
  - create rejects `null`, a number and `"sports"`;
  - create drops an extra `url`;
  - update keeps `category` only when sent, rejects `null` and drops `url`.
- [x] `test_mongo_feed_repository.py` (integration):
  - the stored document includes `category` and `url`;
  - both round-trip, including `url: null`;
  - `BROKEN_DOCUMENTS` gains a missing category, an unknown category and a relative url.
- [x] `test_m0002_feeds_category_and_url.py` (integration):
  - documents without the fields get `"OTHER"` and `null`;
  - existing values are untouched;
  - a second run changes nothing;
  - the index exists and is not unique.
  - `test_migrations_list.py`: the ordered ids are `m0001_feeds_indexes`,
    `m0002_feeds_category_and_url`. This is a single unit test: `tests/test_mongo.py` uses that
    module as its sample and expects exactly one unit test in it.
- [x] App tests:
  - `test_create_feed.py`: `PUT` without `category`, with `null` or with an unknown value gives
    400; with `url` in the body, the feed is stored with `url: null`.
  - `test_update_feed.py`: `PATCH {"category": "SPORTS"}` gives 200 and sets `updated_at`. The
    same category leaves `updated_at` unchanged. `null` gives 400. An extra `url` is ignored.
  - `test_feed_json.py`: `FEED_KEYS` has the new order on every route.
  - `test_invalid_stored_feed.py`: an unknown stored category gives 500.
  - ~~A feed stored without the fields reads as `OTHER`/`null` after startup migrations.~~
    Covered by `test_m0002_feeds_category_and_url.py` and the startup-migration tests
    (`test_app.py`, `test_migrations_list.py`): an app-level test would have to seed Mongo before
    the app starts.
- [x] `.feature` files `create`, `find`, `list`, `update`, `delete`, `home` and `scrap`: send or
      store `category`, and expect `category` and `url` in the bodies.
- [x] `test_openapi.py`:
  - the `FeedCategory` enum;
  - the ordered `FeedResponse` properties;
  - `category` required on create and optional on update.

### Implementation

- [x] Add `FeedCategory` and `FeedUrl` to `value_objects.py`.
- [x] Extend `Feed` (fields, `create`, `update`, primitives) and its mothers.
- [x] Extend `FeedCreator` and `FeedChanges` / `FeedUpdater`.
- [x] Update `scrape/front_page.py` to pass `category=FeedCategory.OTHER` and `url=FeedUrl(None)`
      (interim until Phase 3).
- [x] Add `category` to the request schemas. The strict-mode risk was real: strict Pydantic
      answered "Input should be an instance of FeedCategory" for `"SPORTS"`. So `category` is
      `Annotated[FeedCategory, Strict(False)]`. Lax enum validation still rejects `1`, `"sports"`
      and `""`, and OpenAPI keeps the `FeedCategory` `$ref`. add `category`/`url` to `FeedResponse`, and pass `category` from the `PUT` route.
- [x] Read `category` and `url` in `_to_feed`.
- [x] Add `versions/m0002_feeds_category_and_url.py` and append it to `MIGRATIONS`.
- [x] Update the `There are feeds:` step (a required `category` column and an optional `url`
      column), `FeedDocumentMother` and the existing app tests that
      `PUT` without a category.
- [x] Specs: S00 adds `category` and `url` to the Feed glossary entry, adds a `Category` entry and
      adds S09 to its table.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Filter the list by category

`GET /feed/list?category=<value>` returns only that category's feeds, newest first. With no
parameter, the list is unchanged.

### Public contracts

- `GET /feed/list`:
  - optional query parameter `category: FeedCategory | None = None`;
  - an empty or unknown value (case-sensitive) gives 400 `{"error": "query.category: …"}`;
  - the route declares the errors `400, 500`.
- The route builds `FeedCriteria(filters=(Filter("category", category),), order=Order("created_at",
  "desc"))` when the parameter is given, and `LIST_CRITERIA` otherwise.
  `FeedSearcher.execute(criteria)` is unchanged.
- OpenAPI documents the `category` query parameter with the `FeedCategory` enum, and no 422
  appears.

### Tests first

- [x] `test_feed_searcher.py` (in-memory fake): a category criteria returns only that category's
      feeds, newest first.
      This test and the Mongo one passed on the first run: `category` became filterable in
      Phase 1, when it joined `Feed`'s fields. They pin the contract the route relies on.
- [x] `test_mongo_feed_repository.py` (integration): a category filter with `created_at`
      descending returns only that category, newest first.
- [x] `test_list_feeds.py`:
  - `?category=SPORTS` filters;
  - `?category=nope`, `?category=sports` and `?category=` give 400;
  - no parameter returns every feed.
- [x] `list-feed.feature`: a scenario with mixed categories and `?category=SPORTS`. A second scenario
      checks that `?category=sports` answers 400.
- [x] `test_openapi.py`:
  - `/feed/list` has a `category` query parameter referencing `FeedCategory`;
  - its error statuses are `{"400", "500"}`;
  - there is still no 422 or `HTTPValidationError`.

### Implementation

- [x] Add the query parameter and the criteria building to `list_feeds` in `routes/feed.py`. A
      `NEWEST_FIRST` order is shared by `LIST_CRITERIA` and the category criteria.
- [x] Add 400 to the list route's `responses`, and confirm the 422 stripping covers query
      parameters.
- [x] Refactor without changing behavior.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 3: Scraped article URL and category

Each scraped feed stores the resolved link of its article, and its category comes from the
source's table. Articles without a usable link are skipped. This replaces the Phase 1 interim
`OTHER` / `null`.

### Public contracts

- `ScrapeMapping` gains `categories: Mapping[str, FeedCategory]` (default: empty, so everything is
  `OTHER`).
- `extract_feeds(html: str, mapping: ScrapeMapping, now: datetime, page_url: str) -> list[Feed]`.
  `scrape_front_page` passes `str(response.url)`, the URL after redirects.
- Link rule, in this order:
  1. the title element itself, if it is an `<a href>`;
  2. else the closest `<a href>` ancestor of the title;
  3. else the first `<a href>` inside the title;
  4. else the first `<a href>` in the article.
- The link is resolved with `urljoin(page_url, href)`. It is skipped unless `FeedUrl` accepts it
  (blank, or not `http`/`https`). Query and fragment are kept.
- Category: the first segment of the URL path, lowercased, looked up in `mapping.categories`.
  Unknown or empty gives `OTHER`. The host is not checked.
- Each of the five scrapers gets the table from the spec in its `_MAPPING`.
- The 5-per-source limit counts extracted feeds only. Deduplication is unchanged.

### Tests first

- [ ] `test_front_page.py` (inline HTML, `page_url="https://news.example/"`):
  - each link rule is covered: link on the title, around the title, inside the title, in the
    article;
  - a byline link before a wrapped title is not taken;
  - a relative href resolves against `page_url`;
  - an absolute href to another host is kept;
  - query and fragment are kept;
  - an article with no link, a blank href, `mailto:` or `javascript:` is skipped, and the next one
    counts toward 5;
  - the category is found by the first segment, case-insensitive;
  - an unknown segment or an empty path gives `OTHER`;
  - `scrape_front_page` resolves against the final URL after a 301 redirect.
- [ ] One test per scraper: a parametrized sample of its table (for example El Español
      `invertia → ECONOMY`, `omicrono → TECHNOLOGY`; La Vanguardia `local → SOCIETY`; El Mundo
      `juegos → OTHER`). The existing fixture tests also assert each feed's URL and category.
      Fixture hrefs get section paths, e.g. `/deportes/futbol/123.html`, and one article without
      a link.
- [ ] Spec edge cases as tests:
  - El Español `/espana/politica/…` gives `POLITICS`;
  - El Mundo `/juegos/crucigrama/` gives `OTHER` and is still saved;
  - La Razón relative `/deportes/futbol/123.html` gives `https://www.larazon.es/…`, `SPORTS`.
- [ ] Network smoke tests (`@pytest.mark.network`): each feed has an `http(s)` URL on the source's
      host and a `FeedCategory`.
- [ ] `test_scrape_feeds.py` and `scrap-feed.feature`: the expected bodies include the scraped
      `url` and `category`. Counts are unchanged unless a fixture loses an article to the link
      rule.

### Implementation

- [ ] Add `categories` to `ScrapeMapping`, the `page_url` parameter, a `_link(article, mapping)`
      helper and a `_category(url, categories)` helper in `front_page.py`. Remove the interim
      `OTHER` / `None`.
- [ ] Add the per-source tables to the five `*_feed_scraper.py` files.
- [ ] Update the five HTML fixtures with section hrefs (keep El Mundo's ISO-8859-15 bytes).
- [ ] Specs: S06 gets a "See S09" note on the link requirement.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures. Run `uv run pytest -m network` for
      the five smoke tests.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Phases 1 and 2 are implemented. Review Phase 2, commit with `/ai-project-conventional-commit`,
then run `/ai-project-implement-phase` for Phase 3.
