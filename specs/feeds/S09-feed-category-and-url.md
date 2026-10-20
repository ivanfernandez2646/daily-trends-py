# S09 · Feed category and article URL

**Status:** draft · **Fidelity:** new capability, breaks the create contract on purpose (`category` is
required). Depends on S02, S03, S04, S06, S08, I02 and I07.

## Goal
Every feed has a **category** from a fixed list, so readers can browse feeds by topic, and every
scraped feed keeps the **URL of the original article**, so the app always credits and links back to
the newspaper it took the headline from.

## Domain

### `FeedCategory`
A fixed enum, required on every feed (never `null`):

| Value | Meaning |
|---|---|
| `POLITICS` | National politics and government |
| `INTERNATIONAL` | World news |
| `ECONOMY` | Economy, business, markets, housing |
| `SOCIETY` | Society, regional and local news |
| `SPORTS` | Sports |
| `CULTURE` | Culture, books, film, television |
| `TECHNOLOGY` | Technology |
| `SCIENCE` | Science |
| `HEALTH` | Health |
| `OPINION` | Opinion columns and editorials |
| `OTHER` | Anything else, and any section the app does not recognize |

- An unknown value is an invalid argument, like an unknown `FeedSource`.

### `FeedUrl`
- The URL of the original article: an absolute `http` or `https` URL, or `null`.
- Scraped feeds always have one (see below). `CMS` feeds always have `null`: they are written in the
  CMS and have no external article.
- Any other value (relative, another scheme, blank) is an invalid argument.

### `Feed`
- Gains `category` (required) and `url` (nullable). `Feed.create` takes both.
- `update` can change `category` as it changes `title` and `description`: a different category sets
  `updatedAt`; the same category is no change. `url` is never updated.
- `FeedCreatedDomainEvent` is unchanged.

## HTTP

### `PUT /feed/{id}`
- `category` is **required**, a string with one of the `FeedCategory` values.
- Missing, `null`, not a string or not a value of the enum → 400 with the usual error format (S01,
  I06). There is no default: clients that do not send it are rejected.
- `url` is not accepted: an extra `url` field is ignored like any unknown field, and the feed is
  stored with `url: null`.

### `PATCH /feed/{id}`
- `category` is optional, like `title`. Absent keeps the category; a valid value changes it.
- `null` or an invalid value → 400.
- Any feed can be recategorized, scraped ones included: an editor may correct a wrong mapping.
- `url` cannot be changed; an extra `url` field is ignored.

### `GET /feed/list?category=<value>`
- Optional query parameter. Absent → every feed, as before (S03).
- With a valid value → only the feeds of that category, newest first.
- Empty or not a value of the enum → 400. One value only; repeating the parameter keeps the
  framework's default (the last value wins) and is not part of the contract.

### Responses
- Every feed in every response (`PUT`, `GET /feed/{id}`, `PATCH`, `/feed/list`, `/feed/home`,
  `/feed/scrap`) includes `category` and `url`.
- `/feed/home` ignores categories: its selection (S08) is unchanged and it takes no `category`
  parameter.

## Scraping

### Article URL
- For each `article`, the URL is the `href` of the title element when it is a link, else of the first
  link inside the title element, else of the first link inside the article.
- A relative `href` is resolved against the front page URL after redirects (for example
  `https://www.elmundo.es/`).
- An article without a usable link (none, blank, or not `http`/`https` after resolving) is
  **skipped**, like one without author or title: a scraped feed always credits its article. The
  5-per-source limit still counts only extracted feeds.
- The URL is stored as resolved, query string and fragment included.

### Category from the URL
- The category is the first segment of the URL path, lowercased, looked up in the source's table
  below. A segment that is not in the table, or a path without segments, gives `OTHER`.
- The host is not checked: a link to another site is looked up the same way and usually gives
  `OTHER`.
- The tables live in each scraper's mapping (infrastructure); the domain only knows the enum.

| Category | El Mundo | El Español | El Confidencial | La Razón | La Vanguardia |
|---|---|---|---|---|---|
| `POLITICS` | `espana`, `elecciones` | `espana`, `politica` | `espana` | `espana` | `politica` |
| `INTERNATIONAL` | `internacional` | `mundo` | `mundo` | `internacional` | `internacional` |
| `ECONOMY` | `economia` | `invertia` | `economia`, `empresas`, `mercados`, `vivienda` | `economia` | `economia`, `dinero` |
| `SOCIETY` | `sociedad`, `madrid`, `cataluna`, `andalucia`, `comunidad-valenciana`, `castilla-y-leon`, `baleares` | `sociedad`, `madrid`, `valencia`, `cataluna`, `andalucia`, `castilla-y-leon` | `sociedad` | `sociedad`, `madrid`, `cataluna`, `andalucia`, `comunidad-valenciana`, `castilla-y-leon` | `vida`, `local` |
| `SPORTS` | `deportes` | `deportes` | `deportes` | `deportes` | `deportes` |
| `CULTURE` | `cultura`, `television` | `cultura` | `cultura` | `cultura` | `cultura`, `television` |
| `TECHNOLOGY` | `tecnologia` | `omicrono` | `tecnologia` | `tecnologia` | `tecnologia` |
| `SCIENCE` | `ciencia` | `ciencia` | `ciencia` | `ciencia` | `ciencia` |
| `HEALTH` | `salud` | `salud` | `salud` | `salud` | `salud` |
| `OPINION` | `opinion` | `opinion` | `opinion` | `opinion` | `opinion` |

- Sections seen on the front pages on 2026-10-20 and deliberately left as `OTHER`: El Mundo `juegos`
  (crosswords, sudoku) and `papel`, El Español `reportajes`, El Confidencial `juridico` and `motor`,
  La Vanguardia `lacontra`, `comer` and `historiayvida`.
- Deduplication (I02) is unchanged: source + title + day, not the URL.

## Persistence
- Stored documents gain `category` (string) and `url` (string or `null`).
- A migration (I07) reshapes the existing feeds: every document without `category` gets `OTHER`, and
  every document without `url` gets `null`. Running it twice changes nothing.
- The same migration creates the index `category: 1, createdAt: -1` for the filtered list.
- A stored document with a missing or unknown `category`, or an invalid `url`, is an invalid stored
  feed (I09): 500 on the routes that read it.

## Unchanged
- The front-page selection and staleness (S07, S08, I03), the scraping rules other than the link
  requirement (S06, I02, S08), error mapping (I01, I06, I08).
- Feeds are not reclassified when a table changes: a stored category stays until a `PATCH`.

## Edge cases
- `https://www.elespanol.com/espana/politica/20261020/...` → first segment `espana` → `POLITICS`.
- `https://www.elmundo.es/juegos/crucigrama/` → `OTHER` (and its feed is still saved).
- `https://www.lavanguardia.com/local/valencia/...` → `SOCIETY`.
- A title link `href="/deportes/futbol/123.html"` on La Razón → `https://www.larazon.es/deportes/futbol/123.html`, `SPORTS`.
- An `article` with author and title but no link → skipped; the next article is tried.
- `PUT` without `category` → 400. `PATCH {"category": null}` → 400. `PATCH {"category": "SPORTS"}`
  on a feed already in `SPORTS` → 200, `updatedAt` unchanged.
- `/feed/list?category=sports` (lowercase) → 400: values are case-sensitive, like `source`.
- A feed stored before this spec → `category: "OTHER"`, `url: null` after startup.

## Acceptance criteria
- Domain: `FeedCategory` accepts its 11 values and rejects others; `FeedUrl` accepts absolute
  `http`/`https` and `null`, rejects relative, `ftp:` and blank; `update` changes the category and
  sets `updatedAt`, the same category is no change; `FeedMother` builds feeds with a category and a
  URL.
- Front-page extraction tests with HTML fixtures: link from the title, from inside the title, from the
  article; relative resolution against the final URL; an article without a usable link is skipped;
  the category lookup per table, case-insensitive on the segment, `OTHER` for unknown sections and an
  empty path.
- One test per scraper that its table maps a sample of its sections (the table above is the source of
  truth).
- Use-case tests: create requires a category and stores `url: null`; update changes the category;
  the list use case filters by category.
- Router tests: `PUT` without, with `null`, with an unknown `category` → 400; `PATCH` with a new
  category → 200 and `updatedAt` set, with `null` → 400; `/feed/list?category=SPORTS` filters,
  `?category=nope` and `?category=` → 400; every response includes `category` and `url`.
- Repository integration tests against real Mongo: category and URL round-trip; the filtered search;
  a document with an unknown category is an invalid stored feed.
- Migration test: run on documents without the fields → `OTHER` and `null`; run twice → no change;
  the index exists.
- The live smoke tests (marker `network`) also check that each feed has an `http(s)` URL on the
  source's site and a category.
- The `.feature` files that create feeds (`create`, `find`, `list`, `update`, `delete`, `home`,
  `scrap`) send or store a `category`; the expected bodies include `category` and `url`.
- The OpenAPI document lists `FeedCategory`, marks `category` required on `PUT`, optional on `PATCH`,
  documents the `category` query parameter on `/feed/list`, and `url` (nullable) on every feed.
- `S00` adds `category` and `url` to the Feed glossary entry and S09 to its table.
