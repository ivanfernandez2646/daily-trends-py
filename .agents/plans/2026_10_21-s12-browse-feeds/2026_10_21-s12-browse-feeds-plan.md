---
name: 's12-browse-feeds'
description: 'GET /feed/list answers newest-first pages with an opaque cursor, filters by category, source and Spanish text search, each served by an index'
spec: 'specs/feeds/S12-browse-feeds.md'
branch: 'feat/s12-browse-feeds'
created_at: '2026-10-21T16:00:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-21T19:00:00Z'
---

# S12 · Browse feeds

## Goal

`GET /feed/list` becomes a page: `{"items": [...], "next_cursor": "..." | null}`. Feeds are ordered by
`created_at` and then `id`, both descending, and the list continues from an opaque position cursor.
The query parameters `limit`, `cursor`, `category`, `source` and `q` narrow it. Filters on different
fields combine with AND. `q` uses a Spanish MongoDB text index. Every page without `q` is served by
an index that ends in `createdAt: -1, _id: -1`.

## Context

- **Today:**
  - `list_feeds` builds a `FeedCriteria` and calls `FeedSearcher.execute(criteria) -> list[Feed]`
    ([feed.py](../../../src/daily_trends_py/apps/cms_backend/routes/feed.py)).
  - The shared `Criteria` has OR-only `filters`, a single `order: Order | None` and a `limit`.
  - `MongoRepository._by_criteria` translates them into `$or`, `sort` and `limit`.
  - The in-memory fake mirrors this.
- **Home is unaffected by AND/OR:** `FeedHomeSearcher` only ever filters on `source`, so same-field
  OR keeps its behavior. Its order stays `created_at desc` with no `id` tie-break: the spec leaves
  `/feed/home` unchanged.
- **Error format (agreed):**
  - Query errors keep I06's location, which keeps the `query.` prefix: `query.limit: Input should be
    less than or equal to 100`, `query.cursor: Invalid cursor`, `query.q: Blank search`. The
    existing `query.category: ...` stays as it is.
  - S12's examples are corrected to this format in phase 1.
  - `Invalid cursor` and `Blank search` are raised as `PydanticCustomError`, so the message has no
    `Value error, ` prefix.
- **Criteria design (agreed: generic keyset):**
  - **Shared `Criteria`:**
    - `order: Order | None` becomes `orders: tuple[Order, ...] = ()`.
    - It gains `after: tuple[object, ...] | None`, the position to start after, with one value per
      order. It is only valid with the same number of values as `orders`.
    - It gains `text: str | None`, which is only allowed when the subclass declares
      `TEXT_FIELDS: ClassVar[frozenset[str]]`. It must not be blank.
  - **`FeedCriteria`:**
    - It declares `TEXT_FIELDS = {"title", "description"}`.
    - It allows `after` and `text` only with `LIST_ORDER = (Order("created_at", "desc"),
      Order("id", "desc"))`.
  - **Building criteria:** invalid criteria are still built by code, so they raise `ValueError` like
    today, never a 400.
- **Keyset in Mongo:**
  - **The condition:** for `orders = (o1, o2)` and `after = (v1, v2)`, the query adds
    `{"$or": [{f1: {$lt|$gt: v1}}, {f1: v1, f2: {$lt|$gt: v2}}]}`. This generalises to n orders.
  - **Filters:** one condition per field. A single value is an equality, and several values use
    `{"$in": [...]}`. All of them are ANDed at the top level, which removes today's `$or`.
  - **Text:** `text` adds a top-level `{"$text": {"$search": text}}`. MongoDB only restricts `$text`
    *inside* an `$or`, and the keyset `$or` sits beside it. The integration tests confirm this.
- **Ids:** `_id` is the UUID string, so `id desc` is a string order. The fake compares the same
  strings.
- **Position:**
  - **Domain:** `FeedPosition(created_at: datetime, id: FeedId)` is a frozen dataclass in the feeds
    domain. The use case turns it into `after=(created_at, id.value)`.
  - **Cursor:** the cursor is URL-safe base64 of `{"created_at": "<ISO-8601 Z>", "id": "<uuid>"}`.
    Only `apps/cms_backend` encodes and decodes it.
  - **Valid dates:** the decoder accepts only timezone-aware dates with a zero UTC offset.
  - **Precision:** Mongo keeps milliseconds. A cursor always comes from a feed read back from the
    repository, so the dates match.
- **Use case:** `FeedSearcher` keeps its name and module, and its signature changes. It is only used
  by `/feed/list`, its provider and its tests.
- **Fake text matching:**
  - Words are normalised with NFKD, accents stripped and casefolded.
  - A feed matches when any query word is a whole word of its title or description.
  - Stems and stop words are left to the Mongo integration tests.
- **Migration `m0004_feeds_list_indexes`:**
  - **Drops:** `created_at_desc`, `category_created_at_desc` and `source_created_at_desc`. An index
    that is already gone is ignored: catch `OperationFailure` code 27, `IndexNotFound`.
  - **Creates:** `created_at_id_desc`, `category_created_at_id_desc`,
    `source_created_at_id_desc` and, in phase 3, `title_description_text` with
    `default_language="spanish"`.
  - **Keeps:** `source_title_created_at`, the deduplication index.
  - **Editing it:** the migration is not on `main` yet, so phase 3 can add to it.
- **Docs:**
  - `S00`: "Pagination" leaves the out-of-scope line.
  - `S03`: gets a "Superseded by S12" note on the response.
  - `README.md`: the `/feed/list` row describes the page and its parameters.
  - `improvements/README.md` already links S12.

## Phases

## Phase 1: Filter by source, AND across fields

`?source=` narrows `/feed/list`. Filters on different fields combine with AND and filters on the same
field with OR. The response is still an array.

### Public contracts

- **`Criteria`:**
  - The docstring says: filters on different fields are ANDed, and filters on the same field are
    ORed.
  - `values_by_field() -> Mapping[str, tuple[object, ...]]`: the accepted values of each filtered
    field, in filter order.
  - Fields are otherwise unchanged in this phase.
- **`MongoRepository._by_criteria`:** one condition per field, an equality or `$in`, ANDed.
- **`InMemoryFeedRepository.search`:** the same rules.
- **`FeedSearcher`:** unchanged in this phase.
- **`GET /feed/list`:**
  - It gains `source: FeedSource | None = None`, with the same rules as `category`: an empty or
    unknown value → 400 `query.source: Input should be ...`.
  - `?category=X&source=Y` answers only the feeds that match both.
- **Spec S12:** the error examples get the `query.` prefix.

### Tests first

- [x] `test_criteria.py`: `values_by_field()` groups the values of each field in filter order, and
      is empty without filters. The AND/OR rule lives in the domain, and both adapters use it.
- [x] `test_in_memory_feed_repository.py`:
  - [x] two fields are ANDed;
  - [x] the same field twice is ORed;
  - [x] the same field twice plus another field is `(a OR b) AND c`.
- [x] `test_mongo_feed_repository.py`: the same three cases against real Mongo.
- [x] `test_list_feeds.py`:
  - [x] `?source=CMS` answers only API feeds;
  - [x] `?category=SPORTS&source=EL_MUNDO` answers the intersection;
  - [x] `source` with `nope`, `el_mundo` or empty → 400 with the enum message.
- [x] `test_feed_home_searcher.py`: the existing tests stay green, with no change.

### Implementation

- [x] Group filters by field with `Criteria.values_by_field()` in `_by_criteria` and in the fake.
- [x] Add `source` to `list_feeds` and build the filters from whichever of `category` and `source`
      are present.
- [x] Fix S12's error examples.
- [x] `test_openapi.py`: the list documents the `category` and `source` parameters.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Pages and cursor

The contract break: `/feed/list` answers `{"items", "next_cursor"}`, takes `limit` and `cursor`, and
pages by keyset over `created_at desc, id desc`. A new migration gives each list query its index.

### Public contracts

- **Shared `Criteria`:**
  - **Orders:** `orders: tuple[Order, ...] = ()` replaces `order`. `FeedHomeSearcher`, the fake and
    `_by_criteria` follow the change.
  - **Position:** `after: tuple[object, ...] | None = None`. A length other than `len(orders)` →
    `ValueError`.
- **`FeedCriteria`:**
  - `LIST_ORDER: ClassVar[tuple[Order, Order]] = (Order("created_at", "desc"), Order("id", "desc"))`.
  - `after` with any other `orders` → `ValueError`.
- **Feeds domain:** `FeedPosition(created_at: FeedCreatedAt, id: FeedId)` in
  `domain/feed_position.py`, frozen, with `FeedPosition.of(feed)`. *Implemented with the value
  objects instead of a bare `datetime`: they reject a naive date and keep the millisecond precision
  of storage.*
- **Feeds application:**
  - `FeedPage(feeds: list[Feed], next: FeedPosition | None)` is a frozen dataclass next to the use
    case.
  - `FeedSearcher.execute(*, limit: int, after: FeedPosition | None = None, category: FeedCategory
    | None = None, source: FeedSource | None = None) -> FeedPage`.
  - It asks for `limit + 1` with `LIST_ORDER`, and `next` is the position of the last returned feed
    only when more exist.
  - A limit below 1 raises `ValueError`: it is a bug in the caller, never a 400.
- **`MongoRepository._by_criteria`:** adds the keyset `$or` for `after`, and sorts by every order.
- **HTTP:**
  - **`routes/feed_cursor.py`:**
    - `encode_cursor(position: FeedPosition) -> str`.
    - `decode_cursor(value: str) -> FeedPosition`, which raises `ValueError("Invalid cursor")`.
    - *Implemented as a route dependency, `_after(cursor: str | None) -> FeedPosition | None`,
      instead of an `AfterValidator`: FastAPI rejects a query parameter whose type is not a scalar.
      The dependency raises a `RequestValidationError` at `("query", "cursor")`, so the 400 has the
      usual format.*
  - **`feed_schemas.FeedPageResponse`:** `items: list[FeedResponse]`, `next_cursor: str | None`.
  - **`GET /feed/list`:**
    - The parameters are `limit: Annotated[int, Query(ge=1, le=100)] = 20` and `cursor: str | None`
      (decoded), plus `category` and `source`.
    - It answers `FeedPageResponse`.
    - The docstring says newest first, and the OpenAPI document shows the bounds.
- **Migration `m0004_feeds_list_indexes`:** the three date indexes are replaced, as described in
  Context. It is appended to `MIGRATIONS`.
- **`list-feed.feature`:**
  - The existing scenarios read `items`.
  - A new scenario reads page 1 with `limit=2`, then the `next_cursor` page, and the last page has
    `next_cursor: null`.
  - This needs a step that follows the previous `next_cursor`: `When I request the next page`.
- **Other readers of `/feed/list`:**
  - `scrap-feed.feature` asks for `limit=100` and uses a new step, `The response is a page with
    {n} items`, because it counts up to 27 feeds.
  - `test_scrape_feeds.py` and `test_feed_json.py` read `items`.

### Tests first

- [x] `test_criteria.py`:
  - [x] multiple orders;
  - [x] `after` with the wrong length, or without orders → `ValueError`;
  - [x] an invalid limit still fails.
- [x] `test_feed_criteria.py`: `after` only with `LIST_ORDER`, and an unknown order field still
      fails.
- [x] `test_in_memory_feed_repository.py`:
  - [x] the order with ties broken by `id`;
  - [x] `after` answers strictly after the position;
  - [x] the position of a deleted feed still works.
- [x] `test_feed_searcher.py`, with the fake:
  - [x] 45 feeds and limit 20 → 20, 20 and 5, and only the last page has no `next`;
  - [x] exactly 40 feeds → the second page has no `next`;
  - [x] 5 feeds with the same `created_at` and limit 2 → pages of 2, 2 and 1 by `id` desc, each feed
        once;
  - [x] 25 feeds saved between page 2 and page 3 do not shift page 3;
  - [x] category and source with a position;
  - [x] the repository is asked for `limit + 1`. `InMemoryFeedRepository.searched_criteria` records
        the criteria;
  - [x] a limit below 1 raises `ValueError`.
- [x] `test_mongo_feed_repository.py`: the order with ties, `after`, the position of a deleted
      feed, and a filter combined with `after`.
- [x] `test_m0004_feeds_list_indexes.py`:
  - [x] the three new indexes exist and the three old ones are gone;
  - [x] the deduplication index stays;
  - [x] running it twice changes nothing;
  - [x] it runs on a database where the old indexes were never created;
  - [x] `explain()` uses `created_at_id_desc`, `category_created_at_id_desc` and
        `source_created_at_id_desc` for the list, `?category=` and `?source=` queries;
  - [x] the `MIGRATIONS` list test includes m0004.
- [x] `test_feed_cursor.py` (apps):
  - [x] the round trip;
  - [x] the encoded form is URL-safe base64 of the UTC date and the id;
  - [x] not base64, not ASCII, not UTF-8, not JSON, not an object, missing keys, values that are not
        strings, a naive date, a non-UTC offset or a non-UUID id → `ValueError("Invalid cursor")`.
- [x] `test_list_feeds.py`:
  - [x] the default limit of 20;
  - [x] `limit` set to 0, 101, `abc` or empty → 400 `query.limit: ...`, and 1 and 100 are accepted;
  - [x] `next_cursor` round-trips to the next page;
  - [x] `?cursor=abc` and an empty cursor → 400 `query.cursor: Invalid cursor`;
  - [x] an empty list → `{"items": [], "next_cursor": null}`;
  - [x] the existing tests are adapted to `items`.
- [x] `test_openapi.py`: `/feed/list` answers `FeedPageResponse` and says newest first, and `limit`
      has a minimum of 1, a maximum of 100 and a default of 20. The four parameters are listed.

### Implementation

- [x] Change `order` to `orders` and add `after` in `Criteria`, then add the `FeedCriteria` rules.
- [x] Add the keyset and multi-order sort to `_by_criteria` and to the fake.
- [x] Add `FeedPosition`, `FeedPage` and the new `FeedSearcher.execute`.
- [x] Add the cursor codec, `FeedPageResponse` and the new `list_feeds` signature.
- [x] Add m0004 and register it.
- [x] Update `list-feed.feature`, and add the step that follows the cursor in `conftest.py`.
- [x] Adapt the other readers of `/feed/list`: `scrap-feed.feature`, `test_scrape_feeds.py` and
      `test_feed_json.py`.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 3: Text search and docs

`?q=` searches title and description through a Spanish text index, keeps the newest-first order and
combines with every other filter and with the cursor. The docs follow.

### Public contracts

- **Shared `Criteria`:**
  - `TEXT_FIELDS: ClassVar[frozenset[str]] = frozenset()` and `text: str | None = None`.
  - `text` without `TEXT_FIELDS`, or blank → `ValueError`.
- **`FeedCriteria`:**
  - `TEXT_FIELDS = frozenset({"title", "description"})`.
  - `text` only with `LIST_ORDER` → otherwise `ValueError`.
- **`MongoRepository._by_criteria`:** adds `{"$text": {"$search": text}}`.
- **`InMemoryFeedRepository`:** whole-word, case- and accent-insensitive, any-word match on
  `TEXT_FIELDS`.
- **`FeedSearcher.execute`:** gains `text: str | None = None`.
- **`GET /feed/list`:**
  - It gains `q: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100),
    AfterValidator(_not_blank)]`.
  - A blank value → 400 `query.q: Blank search`.
  - More than 100 characters after trimming → 400 `query.q: String should have at most 100
    characters`.
- **m0004:** also creates `title_description_text`: `[("title", TEXT), ("description", TEXT)]` with
  `default_language="spanish"`.
- **`list-feed.feature`:** a new scenario browses with `category`, `source` and `q` together.
- **Docs:**
  - `S00`: drop "Pagination" from out of scope.
  - `S03`: add the "Superseded by S12" note.
  - `README.md`: update the `/feed/list` row.
  - `S12`: set the status if the workflow does so.

### Tests first

- [ ] `test_criteria.py` and `test_feed_criteria.py`:
  - [ ] text without `TEXT_FIELDS` or with a blank value is rejected;
  - [ ] text only with `LIST_ORDER`.
- [ ] `test_in_memory_feed_repository.py`:
  - [ ] `futbol` finds `Fútbol`;
  - [ ] `fut` finds nothing;
  - [ ] `madrid barcelona` finds either;
  - [ ] the match covers the description;
  - [ ] text is ANDed with the filters.
- [ ] `test_feed_searcher.py`: text alone, with category and source, and with a position.
- [ ] `test_mongo_feed_repository.py`:
  - [ ] `elecciones` finds `elección`;
  - [ ] `Sánchez` finds `sanchez`;
  - [ ] `elec` finds nothing;
  - [ ] `el de` finds nothing;
  - [ ] any word matches;
  - [ ] newest first, not by relevance;
  - [ ] text combined with filters and with `after`.
- [ ] `test_m0004_feeds_list_indexes.py`: the text index exists with the Spanish language, and
      running the migration twice changes nothing.
- [ ] `test_list_feeds.py`:
  - [ ] `?q=%20%20` → 400 `query.q: Blank search`;
  - [ ] 101 characters → 400;
  - [ ] the value is trimmed;
  - [ ] all filters combined.
- [ ] `test_openapi.py`: the five parameters with their bounds and enums.

### Implementation

- [ ] Add `text` and `TEXT_FIELDS` to `Criteria`, and the `FeedCriteria` rule.
- [ ] Add `$text` in `_by_criteria`, and word matching in the fake.
- [ ] Thread `text` through `FeedSearcher` and the router, adding the `q` validator.
- [ ] Add the text index to m0004.
- [ ] Add the feature scenario.
- [ ] Update S00, S03 and the README.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Phases 1 and 2 are implemented. After review, run `/ai-project-implement-phase` for Phase 3 on
`feat/s12-browse-feeds`.
