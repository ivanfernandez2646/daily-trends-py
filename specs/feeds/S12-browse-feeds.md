# S12 · Browse feeds

**Status:** draft · **Fidelity:** new capability, breaks the `/feed/list` contract on purpose (the
response becomes a page). Depends on S03, S08, S09, I05, I07 and I08. Resolves the pagination half of
improvement #15 from `improvements/README.md`.

## Goal
Let a client browse every stored feed page by page, newest first, and narrow the list by category,
by source and by words in the headline, so a reader can scroll through the news and an administrator
can find the feed to edit. With the scraping of S08 (up to 25 feeds per run) the list grows by
hundreds of feeds a day, so answering it whole is no longer an option.

## `GET /feed/list`
Replaces the response of S03; the `category` parameter keeps the rules of S09.

### Query parameters
| Parameter | Type | Default | Rule |
|---|---|---|---|
| `limit` | integer | `20` | From 1 to 100. |
| `cursor` | string | absent | The `next_cursor` of a previous page. Absent → the first page. |
| `category` | `FeedCategory` | absent | As in S09: only feeds of that category. |
| `source` | `FeedSource` | absent | Only feeds of that source, `CMS` included. Same rules as `category`. |
| `q` | string | absent | Words to look for in the title and the description (see *Text search*). |

- The filters combine with **AND**: `?category=SPORTS&source=EL_MUNDO&q=madrid` answers El Mundo
  sports feeds that mention Madrid. Each parameter takes one value; repeating it keeps the
  framework's default (the last value wins) and is not part of the contract.
- A `limit` that is not an integer, or out of range → 400. An empty or unknown `category` or `source`
  → 400. The messages follow the usual format (S01, I06), for example
  `limit: Input should be less than or equal to 100`.
- Unknown parameters are ignored.

### Response
200 with a page:

```json
{
  "items": [{"id": "…", "title": "…", "category": "SPORTS", "url": "https://…", "…": "…"}],
  "next_cursor": "eyJjcmVhdGVkX2F0Ijoi…"
}
```

- `items`: up to `limit` feeds with the same shape as every other feed response (S02, S09).
- `next_cursor`: an opaque string to ask for the next page, or `null` when this page is the last one.
  A page with exactly `limit` items and nothing after it has `next_cursor: null`: the client never
  asks for an empty page.
- No results → `{"items": [], "next_cursor": null}`.
- There is no total count: counting a filtered collection on every page costs more than it gives a
  feed reader.

### Order and cursor
- Feeds are ordered by `created_at` descending, then by `id` descending. The `id` breaks ties: every
  feed of one scraper batch shares its `created_at` (S08), so `created_at` alone would split a batch
  between two pages in no fixed order.
- The cursor is a **position**: the `created_at` and `id` of the last item of the page. The next page
  answers the feeds strictly after that position in the order above. Feeds saved after the first page
  was read never move a page, so a client scrolling while a scraping run saves feeds sees no
  duplicates and skips nothing; the new feeds appear when it starts again from the first page.
- The cursor is opaque to clients: URL-safe base64 of a small JSON document, encoded and decoded in
  the HTTP layer (`apps/cms_backend`). The application and the domain only know the position.
- A cursor that is not valid base64, not the expected JSON, has a date that is not an ISO-8601 UTC
  instant or an `id` that is not a UUID → 400 `cursor: Invalid cursor`.
- A cursor carries no filters. Using a cursor with other filters than the page it came from is not
  an error: the answer is the feeds after that position that match the new filters.
- A cursor whose feed was deleted still works: it is a position, not a reference to a stored feed.

### Text search
- `q` is trimmed. Blank after trimming → 400 `q: Blank search`. Longer than 100 characters → 400.
- The search uses a MongoDB **text index** over `title` and `description` with the Spanish language:
  it ignores case and accents and matches word stems, so `elecciones` finds `elección` and
  `Sánchez` finds `sanchez`. It does not match fragments: `elec` finds nothing.
- Spanish stop words are ignored: `q=el de` finds nothing.
- Several words keep MongoDB's default: a feed matches when it contains **any** of them
  (`q=sánchez feijóo` finds feeds about either). Quotes and a leading `-` keep MongoDB's meaning
  (phrase, exclusion) and are not part of the contract. Requiring every word is a later improvement.
- Results keep the order above, not relevance: the list is a news feed, and the newest match comes
  first.

## Domain and application
- Criteria (I05) gain:
  - filters on **different fields** combine with AND; filters on the **same field** keep combining
    with OR, which is what the home search uses (S08);
  - an optional **text** condition, meaning the words above;
  - an optional **position** to start after, for an order of `created_at` descending and `id`
    descending.
- The list use case takes the filters, the text, the position and the limit, and answers the page:
  the feeds and the position to continue from, or none when there are no more. It asks the repository
  for `limit + 1` feeds to know whether another page exists.
- The in-memory fake repository applies the AND/OR rules, the position and the limit. For the text it
  matches whole words, case- and accent-insensitive, without stems: stems and stop words are checked
  only by the Mongo integration tests.
- `/feed/home` (S08) is unchanged and does not use the position or the text.

## Persistence
- A new migration (I07) replaces the list indexes so every filtered page is served by an index that
  ends in `createdAt: -1, _id: -1`:

  | Index | Serves | Replaces |
  |---|---|---|
  | `createdAt: -1, _id: -1` | the whole list | `created_at_desc` (I08) |
  | `category: 1, createdAt: -1, _id: -1` | `?category=` | `category_created_at_desc` (S09) |
  | `source: 1, createdAt: -1, _id: -1` | `?source=` and the home search | `source_created_at_desc` (I08) |
  | text: `title`, `description`, `default_language: "spanish"` | `?q=` | — |

- The deduplication index `source: 1, title: 1, createdAt: 1` (I02, I08) stays.
- Running the migration twice changes nothing. Dropping an index that does not exist is not an error.
- A search with `q` cannot use the date indexes for its order: MongoDB sorts the matches of the text
  index, bounded by `limit + 1`. This is acceptable for the expected volume (thousands of feeds).

## Unchanged
- `GET /feed/{id}`, `PUT`, `PATCH`, `DELETE`, `/feed/home` and `/feed/scrap`, their bodies and errors.
- The feed shape (S02, S09) and the date format (I06).
- Authentication (S11): `/feed/list` stays public.

## Edge cases
- 45 feeds, `limit=20` → pages of 20, 20 and 5; the first two have a `next_cursor`, the third
  `null`. Exactly 40 feeds → the second page has `next_cursor: null`.
- A scraping run saves 25 feeds while a client is on page 2 → page 3 continues where page 2 ended;
  the 25 new feeds are only on a new first page.
- 5 feeds of one batch with the same `created_at` and `limit=2` → pages of 2, 2 and 1 by `id`
  descending, every feed exactly once.
- `?limit=0`, `?limit=101`, `?limit=abc` → 400.
- `?cursor=abc` → 400 `cursor: Invalid cursor`.
- `?source=CMS` → only the feeds created through the API.
- `?q=%20%20` → 400 `q: Blank search`.
- `?q=futbol` finds a title with `Fútbol`; `?q=fut` finds nothing.
- `?q=madrid barcelona` finds feeds that mention either city, newest first.
- `?category=sports` → 400 (values are case-sensitive, S09).

## Out of scope
Requiring every word of `q`, ordering by relevance, fragment or fuzzy matching, a filter by author,
several values per filter, and a total count.

## Acceptance criteria
- Domain tests: criteria combine different fields with AND and the same field with OR; the position
  and the text are accepted only with the list order; an invalid limit still fails.
- Use-case tests with the in-memory fake: pages in order with `limit + 1`; the last page has no next
  position; ties on `created_at` broken by `id`; feeds saved between two pages do not shift them;
  filters by category, source and text, alone and together.
- Router tests: the default limit, the bounds, `next_cursor` round-trips to the next page; an invalid
  cursor, an empty or unknown `source`, a blank or too long `q` → 400; the response shape on an empty
  list.
- Repository integration tests against real Mongo: the order with ties, the position, each filter and
  their combination, Spanish stems, accents, stop words and no fragment match.
- Migration test: the four indexes exist, the replaced ones are gone, and running it twice changes
  nothing. A query plan check that a page with and without `category` or `source` uses its index.
- The `list` `.feature` file reads `items` and covers a second page; a new scenario browses with
  filters.
- The OpenAPI document describes the page schema, the five query parameters with their bounds and
  enums, and that the order is newest first.
- `S00` lists S12 and no longer has pagination out of scope; `S03` gets a "Superseded by S12" note
  on its response; `improvements/README.md` links S12 for the pagination half of #15.
- The quality gate from `AGENTS.md` passes.
