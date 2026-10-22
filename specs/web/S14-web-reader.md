# S14 · Web app and reader

**Status:** implemented · **Fidelity:** new app, additive (the API gains one command and no route
changes). Depends on S07, S08, S09 and S12. Its look is the [Tinta design system](design-system.md).
The CMS is S15.

## Goal
A web app for the API, living in this repository so that an API change and its frontend change
travel in the same pull request. This spec sets up the app (stack, contract with the API, design
system, quality gate, CI, end-to-end harness) and builds the public **reader**: the front page, a
browse page by topic, newspaper and words, and the detail of a feed, always crediting and linking to
the original article.

## Location and stack
- A `web/` folder at the repository root, next to `src/` and `tests/`. The Python tooling (ruff,
  pyright, import-linter, pytest) does not look at it, and the web tooling does not look outside it.
- Node: the active LTS, pinned in `web/.nvmrc` and `engines`. Packages with **pnpm**, pinned through
  `packageManager` (Corepack). The lockfile is committed.

| Concern | Choice |
|---|---|
| Build and dev server | Vite |
| UI | React, TypeScript in `strict` mode, no `any` without a comment that justifies it |
| Routing | TanStack Router, file-based routes, typed and validated search params |
| Server state | TanStack Query: caching, infinite pages, invalidation after writes |
| API client | `openapi-typescript` types from the API's OpenAPI document and `openapi-fetch` |
| Styles and components | Tailwind CSS with the Tinta tokens, shadcn/ui components copied into the project |
| Fonts and icons | `@fontsource-variable/newsreader`, `@fontsource-variable/inter`, `lucide-react` |
| Lint and format | Biome |
| Unit and component tests | Vitest, Testing Library and MSW |
| End-to-end tests | Playwright |

## Structure
```
web/
  openapi.json          # the API contract, generated (see below), committed
  src/
    api/                # generated types, the typed client, one query module per resource
    features/feeds/     # reader components and hooks (S15 adds the CMS ones)
    components/ui/      # Tinta components on shadcn/ui primitives
    routes/             # TanStack Router file routes
    lib/                # formatting (dates, labels) and small helpers
    styles/             # tokens and global styles
  tests/e2e/            # Playwright
```
- Components never call `fetch`: they use the query and mutation hooks of `src/api`, which use the
  typed client. A response type always comes from the generated types, never from a hand-written
  interface.
- Tests use MSW as a fake API that answers like the real one (same bodies and errors), in line with
  the "fakes, not mocks" rule of `AGENTS.md`. No module mocking (`vi.mock`).

## API contract
- The API gains a subcommand that prints its OpenAPI document without starting the server or
  connecting to Mongo: `uv run daily-trends-py openapi`. It sits next to `create-admin` (S11) when
  that exists, and is the first subcommand otherwise.
- `pnpm api:generate` runs it, writes `web/openapi.json` and regenerates the types in `src/api`.
- CI regenerates both and **fails if they differ** from the committed files: a change to a route or a
  schema that is not reflected in the frontend breaks the build of that pull request.

## Configuration
- `pnpm dev` serves the app on `http://localhost:5173` and proxies `/feed`, `/auth` and `/status` to
  the API at `http://localhost:<PORT>`, where `PORT` is read from the repository's root `.env`
  (default `5000`; `5123` on macOS when AirPlay takes 5000, see `README.md`). In development the
  browser talks to one origin, so CORS plays no part.
- `VITE_API_BASE_URL` sets the API origin for a build; absent, the app calls its own origin.
  Deployment and CORS are out of scope.

## Language and formatting
- The interface is in **Spanish**; code, comments, tests and commits stay in English (`AGENTS.md`).
- Categories and sources show the Spanish labels of the design system, from one mapping in
  `src/lib`. An unknown value from the API shows its raw value instead of breaking the page.
- Dates show in the `Europe/Madrid` timezone (the business timezone of I04): relative under 24 hours
  (*hace 14 min*, *hace 2 h*), then the day (*20 oct*, with the year when it is not the current one),
  and the full date and time in a `<time datetime>` element.

## Layout
- **Reader header**, on every reader page:
  - front page: a top bar with today's date and *Actualizado hace N min* (from the newest
    `created_at` of the front page), the *Daily Trends* masthead with its tagline, and a section bar
    with *Portada*, six category shortcuts (Política, Internacional, Economía, Deportes, Cultura,
    Tecnología), *Todas las secciones* and *Buscar*, all leading to `/feeds` with the matching filter;
  - other pages: a compact bar with the brand, *Portada*, *Explorar* and *Acceder* (to `/login`, S15).
- **Footer**: the list of scraped newspapers and *Cada noticia enlaza a su fuente original*.
- Below 640 px the section bar folds into a *Secciones* disclosure (`aria-expanded`) that opens the
  sections as a two-column list, and the header shows search and menu buttons. No horizontal
  scrolling anywhere: chip groups wrap onto several lines.

## Screens

### `/` · Front page
- The feeds of `GET /feed/home`, in the order the API gives:
  1. the **first** feed as the lead story (Display headline, lead-in, meta, *Leer en <newspaper>*);
  2. the next **three** as a side column;
  3. the rest under *Más titulares* as a grid of cards, with *Ver todas las noticias →* to `/feeds`.
- With fewer feeds the sections shrink in that order: one feed is a lead alone.
- Each headline links to the feed's detail page; *Leer en <newspaper>* opens `url` in a new tab with
  `rel="noopener noreferrer"`. A feed without `url` (a `CMS` feed) shows no source link.
- No feeds → an empty state: the front page fills when the newspapers are scraped.

### `/feeds` · Browse
- The list of `GET /feed/list` (S12), newest first, as rows with a time column (time, and *Hoy*,
  *Ayer* or the day), category, headline, description and meta.
- Filters:
  - category chips (*Todas* and the 11 categories), one at a time;
  - a newspaper selector (*Todos*, the scraped sources and *Redacción*);
  - a search box that applies after 300 ms without typing or on Enter; clearing it removes `q`.
- A summary line names the active filters, with *Limpiar filtros* when any is set.
- The filters live in the URL search params (`/feeds?category=SPORTS&source=EL_MUNDO&q=madrid`),
  validated by the router: a link can be shared, and back and forward restore the filters. An
  invalid value in the URL is dropped, not sent to the API.
- Pages of 20. *Cargar más* asks for the next page with `next_cursor` and disappears when
  `next_cursor` is `null`. Changing a filter starts again from the first page.
- No results → an empty state that names the active filters and offers to clear them.
- Below 640 px the filters fold into a panel opened from a *Filtros* button that shows how many are
  active.

### `/feeds/$id` · Detail
- The feed of `GET /feed/{id}` on the reading width: category (links to `/feeds?category=…`) and
  newspaper, Display headline, the description as a lead-in, and author, *Publicada* and *Editada*
  (when `updated_at` is set).
- A source panel with the article's host and path, shortened, and *Leer en <newspaper>*. A feed
  without `url` has no panel.
- *Más de <category>*: up to 3 other feeds of the same category (`/feed/list?category=…&limit=4`,
  leaving this one out). Hidden when there are none.
- 404, or an id that is not a UUID (400) → a *not found* page with a link to the front page.

## Errors and loading
- Loading shows skeletons in the shape of the content.
- A network error or a 5xx shows a notice with *Reintentar*, never an empty state. Reads are retried
  once by the query client.
- The API answers `{"error": "<message>"}` (S01); the reader shows its own Spanish message and keeps
  the API message only in the console.

## Accessibility
- Responsive from 360 px wide, with no horizontal page scroll.
- Keyboard reachable, visible focus ring in `accent`, landmarks (`header`, `nav`, `main`, `footer`),
  one `h1` per page, labelled form fields, and the source link says where it goes.
- Light and dark themes follow the system preference.

## Quality gate
From `web/`:

```bash
pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test
```

- `AGENTS.md` gains a *Web* section with these commands and the frontend rules of this spec and of the
  design system, and `README.md` explains how to run the API and the app together.
- CI gains a `web` job (lint, types, contract check, unit tests, build) and an `e2e` job.

## End-to-end tests
- Playwright runs against the real API with Mongo, like the current CI job: the API with `ENV=test`,
  the app built and served by `vite preview`.
- Test data is created through the API or written to Mongo by the E2E setup. Tests never call
  `/feed/scrap`: it hits real websites (S06).
- The harness is shared with S15, which adds an administrator to the setup.
- Scenarios: the front page shows seeded feeds in lead, side and grid and links to their articles;
  browsing filters by category, newspaper and words and loads a second page; the detail shows a feed
  and its related feeds; an unknown id shows the *not found* page.

## Out of scope
The CMS (S15), deployment, a `web` service in `docker-compose.yml`, CORS settings, server-side
rendering and SEO, languages other than Spanish, offline support, a manual theme switch, images,
newspaper logos, and analytics.

## Edge cases
- A feed whose `url` is on another site → the link still opens it; its label names the feed's
  source.
- `/feeds?category=nope` → the filter is dropped and the URL rewritten to `/feeds`.
- Typing `ma`, `mad`, `madrid` quickly → one request for `madrid`; an answer for an older query never
  replaces a newer one.
- The front page has 4 feeds → a lead and a side column of 3, no *Más titulares*.
- The API is down → the front page shows the error notice with *Reintentar*.

## Acceptance criteria
- `uv run daily-trends-py openapi` prints the document without Mongo; a backend test checks it equals
  `app.openapi()`.
- CI fails when `web/openapi.json` or the generated types are out of date.
- The design system's acceptance criteria are met.
- Component tests with MSW for every screen: loading, empty, error and success states; the front-page
  sections for 1, 4 and 10 feeds; filters in the URL and the dropped invalid value; *Cargar más* until
  `next_cursor` is `null`; the debounced search; the related feeds of the detail; the *not found* page.
- Unit tests for the label mappings and the date formatting in `Europe/Madrid`.
- The end-to-end scenarios above pass in CI.
- `S00` lists S14 and adds the web app to the vision; `README.md` and `AGENTS.md` are updated.
- The quality gates of `AGENTS.md` and of this spec pass.
