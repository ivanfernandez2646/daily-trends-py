---
name: 'i05-criteria-and-native-dates'
description: 'Search criteria become a validated domain value object with domain field names that the in-memory fake honours; feed dates are aware UTC datetimes in the domain and BSON dates in Mongo, so ordering and day ranges are chronological'
spec: 'specs/improvements/I05-criteria-and-native-dates.md'
branch: 'fix/i05-criteria-and-native-dates'
created_at: '2026-10-11T10:00:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-11T11:30:00Z'
implemented_at: '2026-10-11T11:30:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# I05 · Search criteria and native dates

## Goal

Resolve improvements #10 and #12. `Criteria` stops being a dictionary shaped like a Mongo query and
becomes a frozen value object: OR filters, an optional order and an optional positive limit, using
domain field names that only the Mongo repository maps to storage names. The in-memory fake applies
criteria, so use-case tests assert results. Feed dates are timezone-aware UTC `datetime`s in the
domain and BSON dates in Mongo, so `/feed/list`, `/feed/home` and the scraping day range compare
dates chronologically. The HTTP contract does not change. The repository stays green after each
phase.

## Context

- Branch `fix/i05-criteria-and-native-dates` is cut from `main`, which contains I01–I04. The I05
  spec edit (no migration) is uncommitted on the branch.
- **No data migration** (agreed during planning): every environment starts with an empty `feeds`
  collection. The spec's migration section was replaced with "No data migration".
- `shared/domain/criteria.py`: `Criteria(TypedDict, total=False)` with `filter`, `sort` and `limit`
  (`0` = no limit). Built in `routes/feed.py:32` (`{"sort": {"createdAt": "desc"}}`) and as
  `HOME_CRITERIA` in `application/home/feed_home_searcher.py`.
- `FeedRepository.search(criteria: Criteria | None = None)`; `FeedSearcher.execute` has the same
  signature. `MongoRepository._by_criteria` turns `filter` into `$or` (with the empty-list guard),
  `sort` into a pymongo sort and `limit` into `limit`.
- `tests/contexts/cms/feeds/fakes/in_memory_feed_repository.py` ignores criteria and records
  `searched_criteria`. `test_feed_searcher.py` and `test_feed_home_searcher.py` assert that list.
  `FailingFeedRepository` also implements `search`.
- Dates: `DateTimeValueObject(StringValueObject)` validates ISO strings; `now()` returns
  `…000Z` text. `FeedPrimitives.createdAt: str`, `updatedAt: str | None`. Routes return
  `feed.to_primitives()` straight to `JSONResponse`.
- String date parsing that disappears: `FeedScraper._run` (`fromisoformat` for the business day),
  `FeedHomeSearcher._is_from_a_previous_day`, `MongoFeedRepository._stored_date`, and the fake's
  `exists_headline`.
- `create_mongo_client` builds `AsyncMongoClient(url)` without `tz_aware`. pymongo then returns
  naive datetimes. BSON keeps only milliseconds.
- The test mothers `FeedCreatedAtMother`, `FeedUpdatedAtMother` and `MotherCreator.iso_date_time()`
  build string dates. `tests/apps/cms_backend/conftest.py` seeds features from ISO strings through
  `FeedMother.from_primitives`. `test_invalid_stored_feed.py` and the Mongo repository test insert
  `createdAt: "not-a-date"` directly.

## Phase 1: Criteria value object (#10)

Criteria are built with domain field names, validated when they are built, and honoured by both
repositories. Dates are still strings in this phase.

### Public contracts

- `shared/domain/criteria.py`:
  ```python
  type SortDirection = Literal["asc", "desc"]


  @dataclass(frozen=True)
  class Filter:
      field: str
      value: object


  @dataclass(frozen=True)
  class Order:
      field: str
      direction: SortDirection


  @dataclass(frozen=True)
  class Criteria:
      FIELDS: ClassVar[frozenset[str]] = frozenset()
      filters: tuple[Filter, ...] = ()
      order: Order | None = None
      limit: int | None = None
  ```
  - `filters` are combined with OR. No filters means every feed. `limit=None` means no limit.
  - `__post_init__` raises `InvalidArgumentError`:
    - a limit that is not a positive `int` (`0`, `-1`, `True`) →
      `<FeedCriteria> does not allow the limit <0>`
    - a filter or order field outside `FIELDS` →
      `<FeedCriteria> does not allow the field <createdAt>`
    - The class name in the message is `type(self).__name__`.
- `feeds/domain/feed_criteria.py`: `class FeedCriteria(Criteria)`. `FIELDS` is the set of `Feed`
  constructor field names (`id`, `title`, `description`, `author`, `source`, `created_at`,
  `updated_at`); the aggregate's `_domain_events` is excluded.
- `FeedRepository.search(self, criteria: FeedCriteria) -> list[Feed]`. Criteria are required; an
  empty `FeedCriteria()` returns every feed.
- `FeedSearcher.execute(self, criteria: FeedCriteria) -> list[Feed]`.
- `HOME_CRITERIA = FeedCriteria(filters=(Filter("source", FeedSource.EL_MUNDO),
  Filter("source", FeedSource.EL_ESPANOL)), order=Order("created_at", "desc"), limit=10)`.
- `/feed/list` searches with `FeedCriteria(order=Order("created_at", "desc"))`.
- `MongoRepository._by_criteria(self, criteria: Criteria, storage_fields: Mapping[str, str])`.
  Fields that are not in the mapping keep their name. `MongoFeedRepository` passes
  `{"id": "_id", "created_at": "createdAt", "updated_at": "updatedAt"}`. No filters → query `{}`.
- `InMemoryFeedRepository.search` applies filters (OR, equality on the field's primitive value),
  order (a `None` value sorts first ascending, as in Mongo), then limit. `searched_criteria` is
  removed.

### Tests first

- [x] `tests/contexts/cms/shared/domain/test_criteria.py` (with a `DummyCriteria` subclass and
  `FIELDS = {"name", "age"}`):
  - no arguments → no filters, no order, no limit;
  - several filters kept in order;
  - an order with a direction;
  - `limit=None` is allowed and a positive limit is kept;
  - `limit` of `0`, `-1` or `True` → `<DummyCriteria> does not allow the limit <…>`;
  - an unknown filter field and an unknown order field → `<DummyCriteria> does not allow the
    field <…>`;
  - criteria with the same values are equal.
- [x] `tests/contexts/cms/feeds/domain/test_feed_criteria.py`: every `Feed` field is accepted;
  `createdAt` (a storage name) is rejected.
- [x] `tests/contexts/cms/feeds/fakes/test_in_memory_feed_repository.py`: no filters returns every
  feed; OR filters on `source`; order by `created_at` in both directions; limit; filter, order and
  limit together.
- [x] `test_feed_searcher.py`: returns only the feeds that match the criteria, in order and
  limited. No assertion on the criteria object.
- [x] `test_feed_home_searcher.py`: replace the `HOME_CRITERIA` equality test and the
  `searched_criteria` assertions with results: `CMS` and `EL_PAIS` feeds are excluded, the newest
  come first, and at most 10 are returned. Keep the staleness tests.
- [x] `test_mongo_feed_repository.py`: switch to `FeedCriteria`. `FeedCriteria()` returns every
  feed; the OR filter; `Order("created_at", "desc"/"asc")`; a limit; no limit returns every feed
  (replaces the `limit: 0` test); a filter on `id` maps to `_id`.
- [x] `tests/apps/cms_backend/test_list_feeds.py` / `test_home_feeds.py` and the features stay
  green unchanged.

### Implementation

- [x] Replace `Criteria` with the value objects above and add `FeedCriteria`.
- [x] Update the `FeedRepository` port, `FeedSearcher`, `HOME_CRITERIA`, the `/feed/list` route,
  `MongoRepository._by_criteria`, `MongoFeedRepository.search`, `InMemoryFeedRepository` and
  `FailingFeedRepository`.
- [x] Remove the empty-`$or` guard comment: no filters now build the query `{}` directly.
- [x] Add "Superseded by I05" to `S03-list-feeds.md` next to the criteria shape (`limit` 0, "Without
  criteria everything is returned"). Link I05 for #10 in `specs/improvements/README.md` (already
  linked: check it).
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Phase 2: Native dates (#12)

Feed dates are aware UTC datetimes truncated to milliseconds in the domain and BSON dates in Mongo.
Responses keep the `…000Z` strings.

### Public contracts

- `shared/domain/date_time_value_object.py`:
  - `DateTimeValueObject.value: datetime | None`; `RequiredDateTimeValueObject.value: datetime`.
  - `__post_init__` accepts only an aware `datetime` (and `None` for the optional one), stores it
    converted to UTC and truncated to milliseconds, and otherwise raises
    `<FeedCreatedAt> does not allow the value <{value}>`. The value is rendered like other raw
    values (`render_value`: a string as is, `None` as `null`), and a naive `datetime` with `str()`,
    so a stored `"not-a-date"` keeps the I01 message. A naive `datetime` is rejected.
  - A document without `createdAt` is read as `createdAt: null`, so it fails with
    `<FeedCreatedAt> does not allow the value <null>` instead of a `KeyError`.
  - `now()` returns `datetime.now(UTC)` truncated to milliseconds.
  - It no longer inherits from `StringValueObject`.
- `FeedPrimitives.createdAt: datetime`, `updatedAt: datetime | None`.
- HTTP: a feed is serialized for JSON by one helper in `apps/cms_backend/routes/feed.py` that
  formats dates as `YYYY-MM-DDTHH:MM:SS.mmmZ` (and keeps `None`). Every feed response uses it. The
  response bodies do not change.
- Mongo: `createdAt`/`updatedAt` are stored as BSON dates; `updatedAt: null` stays `null`.
  `create_mongo_client` builds the client with `tz_aware=True, tzinfo=UTC`.
- `MongoFeedRepository.exists_headline` queries `createdAt` with
  `{"$gte": since, "$lt": until}` as datetimes. `_stored_date` is removed.
- `FeedScraper` and `FeedHomeSearcher` read `feed.created_at.value` as a datetime
  (`.astimezone(tz).date()`) without parsing.
- Test helpers: `FeedCreatedAtMother.create(value: datetime | str)`,
  `FeedUpdatedAtMother.create(value: datetime | str | None)` (an ISO string is parsed, so fixed
  dates stay readable), `MotherCreator.date_time() -> datetime` (aware UTC, milliseconds; replaces
  `iso_date_time()`). The feature
  step converts the table's ISO strings with `datetime.fromisoformat`.

### Tests first

- [x] `test_date_time_value_object.py`:
  - an aware datetime in another offset is stored in UTC;
  - microseconds are truncated to milliseconds;
  - `None` accepted only by the optional one;
  - a string, a number and a naive datetime → `<Dummy…> does not allow the value <…>`;
  - `now()` is aware UTC with milliseconds;
  - equality.
- [x] `test_feed.py`, `test_feed_creator.py`, `test_front_page.py`: compare datetimes instead of
  parsing strings.
- [x] `test_mongo_feed_repository.py`:
  - the stored document holds `datetime` values for `createdAt` (and `updatedAt` when set) and
    `None` when it is null;
  - save then find gives equal primitives;
  - chronological sort across offsets: `2026-10-09T10:00:00+02:00` and `2026-10-09T09:30:00Z`
    → the second is first with `desc`;
  - the business-day range tests use datetimes;
  - a document inserted with `createdAt` as a string (`"not-a-date"` and a valid ISO string) →
    `InvalidStoredFeed` with `<FeedCreatedAt> does not allow the value <…>`; also a number and a
    missing `createdAt` (`<null>`).
- [x] `test_mongo_client_factory.py`: a stored datetime is read back aware in UTC.
- [x] `test_feed_scraper.py` / `test_feed_home_searcher.py`: same business-day cases with datetime
  values.
- [x] `tests/apps/cms_backend`: `test_list_feeds.py` lists two feeds saved with different offsets
  chronologically with `…Z` dates and a `null` `updatedAt`; `test_create_feed.py` checks the
  `createdAt` format; the other route tests keep comparing response bodies;
  `test_invalid_stored_feed.py` stays green; the `list-feed` and `home-feed` features pass
  unchanged.

### Implementation

- [x] Change the date value objects, `FeedPrimitives`, `Feed.from_primitives`/`to_primitives`, the
  mothers and `MotherCreator`.
- [x] Add the JSON helper in the routes and use it in every feed response.
- [x] Create the Mongo client with `tz_aware=True, tzinfo=UTC`. Remove `_stored_date`. Update
  `exists_headline`, `FeedScraper`, `FeedHomeSearcher` and the fake's `exists_headline`.
- [x] Update the feature seeding step to parse table dates.
- [x] Add "Superseded by I05" to `S02-create-and-find-feed.md` ("Dates are stored as ISO-8601
  strings") and `S03-list-feeds.md` ("Ordering is textual"). Check that `README.md` links I05 for
  #12.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Every phase is implemented. Review Phase 2, then commit it with `/ai-project-conventional-commit`.
