---
name: 's14-web-reader'
description: 'A web app in web/ with the Tinta design system, a typed client generated from the API contract, and the public reader: front page, browse and detail'
spec: 'specs/web/S14-web-reader.md'
branch: 'feat/s14-web-reader'
created_at: '2026-10-21T13:00:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-21T22:00:00Z'
implemented_at: '2026-10-21T22:00:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S14 · Web app and reader

## Goal

A `web/` app in this repository, built with Vite, React, TanStack Router and Query, Tailwind and
shadcn/ui. Its API types are generated from the OpenAPI document of the backend, so a contract
change that the frontend does not reflect breaks CI. The app implements the Tinta design system
(`specs/web/design-system.md`) and the public reader:

- `/`: the front page;
- `/feeds`: browse by category, newspaper and words, with the filters in the URL;
- `/feeds/$id`: the detail, with related feeds.

The app is tested with Vitest and MSW, and end to end with Playwright against the real API and
Mongo.

## Context

- **The API gains no route.** It gains one subcommand, `openapi`, next to `create-admin`.
  - `main.py` already has the `argparse` subparsers, and `cli.py` holds the command functions.
  - `create_app(container)` needs a container, but building one connects to nothing: Mongo is
    reached only when a dependency is resolved. `tests/apps/cms_backend/test_openapi.py` already
    builds the document this way, without a database.
- **Agreed:** the `openapi` command ignores the environment and `.env`, because the document
  depends on no setting. It builds the app from the default `Settings` values, so
  `ENV=production` without `MONGO_URL`, or an invalid `TIMEZONE` in `.env`, still prints the same
  document.
- **API used by the reader:** `GET /feed/home`, `GET /feed/list` (`limit`, `cursor`, `category`,
  `source`, `q`; answers `{items, next_cursor}`) and `GET /feed/{id}` (400 for a non-UUID id, 404
  for an unknown one).
  - `FeedResponse` has `id, title, description|null, author, source, category, url|null,
    created_at, updated_at|null`.
  - Dates are UTC with `Z` (I06). Errors are `{"error": "..."}`.
  - CORS already allows any origin, and the reader never needs it: it talks to one origin.
- **Stored feeds** (for the E2E seed):
  - `{_id: <uuid str>, title, description, author, source, category, url, createdAt: Date,
    updatedAt: Date|null}` in the `feeds` collection;
  - the text index of `q` is created by migration `m0005` when the API starts, so documents
    written directly are searchable.
  - `PUT /feed/{id}` only creates `CMS` feeds, and needs a token. The front page only shows
    scraped sources, so the E2E setup writes to Mongo directly.
- **E2E API:** it runs with `SCRAPE_SCHEDULE_ENABLED=false`. Otherwise the startup run would
  scrape the real websites, which S14 forbids.
- **Toolchain:**
  - Node 24, the active LTS on 2026-10-21, is installed. pnpm is not installed, but Corepack
    0.36 is, so pnpm is pinned through `packageManager` and run via Corepack.
  - Package versions are the latest stable ones at install time, pinned by the committed
    lockfile. Tailwind is v4, configured in CSS with `@theme`, and Vitest runs in `jsdom`.
- **Agreed scope cuts:**
  - The compact reader bar has no *Acceder*. S15 adds it together with `/login`, because a typed
    link to a missing route does not compile.
  - The design system's Dialog is built in S15, with its first consumer (the delete
    confirmation).
  - `specs/web/design-system.md` stays a spec as it is. It does not become a `DESIGN.md`.
- **Decisions where the spec is silent:**
  - Under 1 minute, a relative time reads *ahora*.
  - The newspaper selector lists the 5 scraped sources and *Redacción*. The URL also accepts
    `EL_PAIS`, a valid API value for stored feeds, but the selector does not offer it.
  - *Buscar* in the section bar leads to `/feeds` with the search box focused.
- **Generated files are committed and excluded from Biome:** `web/openapi.json`,
  `web/src/api/schema.gen.ts` and TanStack Router's `web/src/routeTree.gen.ts`.
- **Already done:** `S00` already lists S14 in its table. Only the vision text needs the web app.
- **Checkout:** the worktree `s13-admin-session` was removed. Work happens in the main checkout,
  on `feat/s14-web-reader` branched from `main`.

## Phases

## Phase 1: API contract and web scaffold

The backend prints its OpenAPI document, and `web/` exists with its toolchain. `pnpm api:generate`
produces the committed contract and types, a typed client uses them, and CI checks lint, types,
tests, the build and that the contract is up to date. The app renders a minimal root page.

### Public contracts

- CLI: `uv run daily-trends-py openapi`.
  - Writes `json.dumps(app.openapi(), indent=2, ensure_ascii=False)` plus a newline to stdout,
    and exits 0.
  - It reads no environment variable and no `.env`, and does not connect to Mongo.
  - `--help` lists it as "Print the OpenAPI document of the API, without starting it."
- `apps/cms_backend/cli.py`: `def openapi_document() -> dict[str, object]`, the document of an app
  built from the default settings.
- `web/package.json`:
  - `engines.node: ">=24 <25"`, `packageManager: "pnpm@<latest 10.x>"`, and `web/.nvmrc` = `24`;
  - scripts:
    - `dev`, `build` (`tsc --noEmit && vite build`), `preview`;
    - `test` (`vitest run`), `lint` (`biome ci .`), `typecheck` (`tsc --noEmit`);
    - `api:generate`: runs `uv run --project .. daily-trends-py openapi > openapi.json`, then
      `openapi-typescript openapi.json -o src/api/schema.gen.ts`;
    - `e2e` (`playwright test`, from phase 3).
- `web/src/api/client.ts`:
  - `export const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_BASE_URL ?? "" })`;
  - `export class ApiError extends Error { readonly status: number }`, whose message is the API's
    `error`, or the status text when there is no body;
  - `export function unwrap<T>(result: FetchResponse<…>): T`, which throws `ApiError` for any
    non-2xx answer.
- `web/vite.config.ts`: `server.proxy` (inherited by `preview`) sends `/feed`, `/auth` and
  `/status` to `http://localhost:<PORT>`. `PORT` comes from the root `.env` through Vite's
  `loadEnv(mode, "..", "")`, default `5000`, and an `API_PORT` environment variable overrides it
  for E2E.
- `web/src/routes/__root.tsx` and `index.tsx`, which for now renders the page landmarks with an
  `h1` *Daily Trends*.
- CI: job `web` in `.github/workflows/ci.yml` (Ubuntu, Node from `web/.nvmrc`, Corepack, uv):
  - `pnpm install --frozen-lockfile`;
  - `pnpm api:generate && git diff --exit-code -- web/openapi.json web/src/api/schema.gen.ts`;
  - `pnpm lint`, `pnpm typecheck`, `pnpm test` and `pnpm build`.
- `.gitignore`: `web/node_modules/`, `web/dist/`, `web/test-results/`, `web/playwright-report/`.
- `AGENTS.md`: a *Web* section with the commands, the web quality gate and the rules:
  - components call the `src/api` hooks, never `fetch`;
  - response types come only from `schema.gen.ts`;
  - tests use MSW fakes, never `vi.mock`;
  - the UI is in Spanish and the code in English;
  - styles use Tinta tokens only;
  - the API contract is regenerated after a backend change.

### Tests first

- [x] `tests/apps/cms_backend/test_cli.py` or `test_main.py`:
  - `main(["openapi"])` prints JSON equal to
    `create_app(create_container(IsolatedSettings(...))).openapi()`, and exits 0.
- [x] `tests/apps/cms_backend/test_main.py` (subprocess, outside the repository): `openapi` with
  `ENV=production` and without `MONGO_URL` or `AUTH_SECRET_KEY` exits 0 and prints a document
  whose `info.title` is `Daily trends`. Mongo is unreachable (`MONGO_URL` points at a closed
  port), so nothing tries to connect.
- [x] `web/src/api/client.test.ts` (MSW):
  - a 200 from `GET /feed/home` unwraps to the feed array;
  - a 404 `{"error": "Feed not found"}` throws an `ApiError` with status 404 and that message;
  - a network error throws (it is not an `ApiError`).
- [x] `web/src/routes/index.test.tsx`: the root page renders `main` with one `h1`.

### Implementation

- [x] Add the `openapi` subcommand and `openapi_document()`. Build `Settings` without reading the
  environment, with a comment explaining why.
- [x] Scaffold `web/`:
  - Vite with React and TypeScript `strict` (also `noUncheckedIndexedAccess`);
  - TanStack Router with the file-routes plugin, TanStack Query, `openapi-typescript`,
    `openapi-fetch`, Biome, Vitest, Testing Library, MSW and jsdom.
- [x] Add `web/src/test/server.ts`, the MSW server: started in the Vitest setup, failing on any
  unhandled request, and reset after each test. Add response factories under `web/src/test/`
  (feed mothers) typed with the generated `FeedResponse`.
- [x] Run `pnpm api:generate`, and commit `openapi.json`, `schema.gen.ts` and `routeTree.gen.ts`.
- [x] Add the `web` CI job and the `.gitignore` entries.
- [x] Write the *Web* section of `AGENTS.md`. Add a *Web app* section to `README.md`: install,
  `pnpm dev` with the API, and `api:generate`.
- [x] Run the Python quality gate and, from `web/`, `pnpm lint && pnpm typecheck && pnpm test &&
  pnpm build`.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- `openapi_document()` lives in `main.py`, not `cli.py`. It needs `create_app`, and `main.py`
  already imports `cli.py`, so putting it there avoids a circular import. It builds the app with
  `Settings.model_construct()`, the defaults without reading the environment. Both tests are in
  `test_main.py`.
- Versions:
  - pnpm `12.14.0` is the latest stable, newer than the 10.x the plan assumed;
  - TypeScript is `5.9.3`, because `openapi-typescript` needs `typescript ^5.x` (TypeScript 7
    has no compiler JS API);
  - Vite is `8.3.4` and Biome `2.5.15`. The newer releases, from 2026-10-21, fail pnpm's
    `minimumReleaseAge` policy. Older pins were chosen instead of adding exclusions.
- TanStack Query is installed in phase 3, where it is first used, so phase 1 adds no unused
  dependency.
- The client looks up `globalThis.fetch` on each call. `openapi-fetch` would otherwise keep the
  `fetch` it saw at load time, before MSW installs its fake network.
  - `baseUrl` falls back to `window.location.origin`.
  - MSW 3 calls the option `onUnhandledFrame: "error"`; it was checked that an unhandled request
    fails.
  - The setup stubs `window.scrollTo`, which jsdom lacks and the router calls on every
    navigation.
- The proxy keys are anchored (`^/feed/`, `^/auth/`, `^/status$`). A plain `/feed` prefix would
  also proxy the app's own `/feeds` pages on reload.
  - Checked by hand against the real API: `/status` and `/feed/home` reach it through
    `localhost:5173`, and `/feeds?category=SPORTS` serves the app.
- CI also fails when `src/routeTree.gen.ts` changes during the build.
- The web quality gate in `AGENTS.md` and `README.md` has no `pnpm playwright test` yet: phase 3
  adds it.

## Phase 2: Tinta design system

The tokens in both themes, the fonts, the label and date helpers, and the components the reader
needs, each tested by role and state. A component-gallery route is not added: the screens are the
consumers.

### Public contracts

- `web/src/styles/tokens.css`:
  - the color tokens of the spec, as `--color-*` custom properties, with light values on `:root`
    and dark values under `@media (prefers-color-scheme: dark)`;
  - the category marker colors, as `--color-category-<value>`.
- `web/src/styles/global.css`: `@import "tailwindcss"`, then `@theme`:
  - the colors map to the tokens (`bg-paper`, `text-ink`, `border-rule`…);
  - `--font-serif: "Newsreader Variable", Georgia, serif` and `--font-sans: "Inter Variable",
    system-ui, sans-serif`;
  - the type scale (`text-masthead`, `text-display`, `text-title-1`, `text-title-2`, `text-lead`,
    `text-body`, `text-meta`, `text-label`);
  - the radii;
  - the reduced-motion rule.
- `web/src/lib/labels.ts`:
  - `CATEGORIES: readonly FeedCategory[]`, in the spec's order;
  - `READER_SOURCES: readonly FeedSource[]`: `EL_MUNDO`, `EL_ESPANOL`, `EL_CONFIDENCIAL`,
    `LA_RAZON`, `LA_VANGUARDIA` and `CMS`;
  - `categoryLabel(value: string): string` and `sourceLabel(value: string): string`. An unknown
    value answers itself;
  - the label maps are typed `Record<FeedCategory, string>` and `Record<FeedSource, string>`, so a
    new enum value fails to compile.
- `web/src/lib/dates.ts` (all in `Europe/Madrid`; `now` is injectable for tests):
  - `formatRelative(iso: string, now?: Date): string`:
    - *ahora* under 1 min;
    - *hace N min* under 1 h;
    - *hace N h* under 24 h;
    - then *20 oct*, or *20 oct 2025* outside the current year;
  - `formatTimeColumn(iso: string, now?: Date): { time: string; day: string }`: `time` like
    `08:15`, and `day` is *Hoy*, *Ayer* or *20 oct*;
  - `formatFullDate(iso: string): string`, for example *20 de octubre de 2026, 08:15*;
  - `formatToday(now?: Date): string`, for the top bar, for example *martes, 21 de octubre de
    2026*.
- `web/src/components/ui/`:
  - `Button` (`variant: "primary" | "secondary" | "destructive" | "link"`, `size: "default" |
    "dense" | "icon"`);
  - `Chip` (`pressed`, `aria-pressed`);
  - `CategoryLabel` (`category`, optional `linked`);
  - `SourceLink` (`url`, `source`): *Leer en <newspaper>*, `target="_blank"`,
    `rel="noopener noreferrer"`, an outward icon, and an accessible name that says it opens the
    newspaper;
  - `Field`, a labelled input with an optional `error`;
  - `Select`, a native select styled like a field;
  - `Notice` (`tone: "success" | "error"`, with role `status` or `alert`);
  - `Skeleton`;
  - `EmptyState` (`message`, `action`);
  - `Time` (`iso`, `format`), which renders `<time dateTime={iso} title={formatFullDate(iso)}>`.
- `web/src/features/feeds/FeedCard.tsx`: `variant: "lead" | "side" | "grid" | "row" | "compact"`.
  It shows the category label, the headline linked to `/feeds/$id`, the description (clamped to 2
  lines on cards), and the meta line *Source · author · time*.
- `main.tsx` imports `@fontsource-variable/newsreader` and `@fontsource-variable/inter`.

### Tests first

- [x] `web/src/styles/tokens.test.ts`: it parses `tokens.css` and checks that every text and
  background pair passes 4.5:1, in both themes. The pairs:
  - `ink`, `ink-soft`, `meta` and `accent` on `paper`, `surface` and `canvas`;
  - `danger` on `surface`;
  - `surface` on `ink`, the primary button;
  - `success-fg` on `success-bg` and `error-fg` on `error-bg`.

  It also checks that both themes define the same set of tokens.
- [x] `web/src/lib/labels.test.ts`:
  - every category and source has its Spanish label, `EL_PAIS` included;
  - an unknown value answers itself;
  - the order of `CATEGORIES` and of `READER_SOURCES`.
- [x] `web/src/lib/dates.test.ts`:
  - *ahora*, *hace 14 min*, *hace 2 h* and *hace 23 h*;
  - the switch to *20 oct* at 24 h, and the year outside the current year;
  - *Hoy* and *Ayer* decided by the Madrid calendar day, so `2026-10-20T22:30:00Z` is *Hoy* on
    the 21st in Madrid;
  - a date across the DST change (`2026-10-25`).
- [x] One `*.test.tsx` per component:
  - its role and accessible name;
  - its states: a chip toggles `aria-pressed`, a button variant, a field's error linked by
    `aria-describedby`, a notice's role by tone;
  - the source link's `target`, `rel` and accessible name;
  - `Time` renders `datetime`;
  - each `FeedCard` variant, with and without a description.

### Implementation

- [x] Add shadcn/ui (`components.json`, the `cn` helper) and copy only the primitives these
  components use. Restyle them with the tokens: no raw hex outside `tokens.css`.
- [x] Write the tokens, the theme, the fonts and the helpers, then the components.
- [x] Run the web gate and fix failures (Python is unchanged).
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **Tokens:**
  - `tokens.css` holds the raw values as `--paper`, `--ink`… and `--category-<value>`.
  - `global.css` maps them to Tailwind with `@theme inline` (`--color-paper: var(--paper)`), and
    resets Tailwind's default palette (`--color-*: initial`), so no other color class exists.
  - The contrast test reads `tokens.css` from disk, because Vitest does not process CSS imports.
    It also covers `surface` on `danger` (the destructive button) and `error-fg` on the three
    backgrounds (field errors).
  - It was checked that a too-light accent makes the test fail.
- **Type scale:**
  - The Meta style is `text-caption`, because `text-meta` is already the color.
  - `cn` extends `tailwind-merge` with the type scale. Otherwise `text-display` reads as a color
    and is dropped next to `text-ink`.
- **Dates:** `formatFullDate` uses ICU's Spanish format, *20 de octubre de 2026 a las 08:15*,
  instead of the comma in the plan's example.
- **Fonts:** Newsreader loads with the optical size axis (`opsz.css`). The build has no reference
  to an external font host.
- **Components:**
  - `IconButton` requires a `label`, so an icon-only button always has a name.
  - `SourceLink` has a `link` variant and a `button` variant, the primary pill of the detail's
    source panel in the canvas. Its accessible name ends in *(se abre en una pestaña nueva)*.
  - `CategoryLabel` has no `linked` prop yet. A typed link to `/feeds?category=…` needs the
    browse route's search validation (phase 4), so the detail wraps it in a link in phase 5.
  - The component files are kebab-case like shadcn's (`feed-card.tsx`, not `FeedCard.tsx`).
  - Dialog is deferred to S15, as agreed.
- **Detail route:** `src/routes/feeds.$id.tsx` exists as a stub, because the card's typed link
  to `/feeds/$id` needs a registered route. Phase 5 fills it in.
- **Tests:**
  - Callbacks are checked with explicit recorders, not `vi.fn()`.
  - The clock is faked with `vi.useFakeTimers({ toFake: ["Date"] })`.
  - `renderWithRouter` renders a component that holds links inside a router of its own.
- **Versions:** `lucide-react` is `1.60.0`, because `1.61.0` came out today and fails pnpm's
  release-age policy.

## Phase 3: Reader layout, front page and E2E harness

The shared reader layout and `/`, against the real `GET /feed/home`. The Playwright harness runs the
API with Mongo and seeds feeds. CI gains the `e2e` job.

### Public contracts

- `web/src/api/query-client.ts`: `createQueryClient()`.
  - Queries retry once and keep a `staleTime` of 60 s.
  - On an `ApiError` the API message goes to `console.error`. The UI never shows it.
- `web/src/api/feeds.ts`:
  - `feedKeys` (`all`, `home()`, `list(filters)`, `detail(id)`);
  - `useHomeFeeds()`, which uses `homeFeedsQuery`.
- `web/src/features/feeds/front-page.ts`:
  - `splitFrontPage<T>(feeds: T[]): { lead?: T; side: T[]; more: T[] }`;
  - `lastUpdated(feeds): string | undefined`, the newest `created_at`.
- `web/src/features/feeds/` components:
  - `ReaderHeader` (`variant: "front" | "compact"`):
    - the front variant has the top bar with today's date and *Actualizado hace N min*, the
      masthead with its tagline, and `SectionBar`;
    - the compact variant has the brand, *Portada* and *Explorar*;
  - `SectionBar`:
    - *Portada*, the six category links (`/feeds?category=…`), *Todas las secciones* (`/feeds`)
      and *Buscar*;
    - below 640 px, a *Secciones* button with `aria-expanded` opens a two-column list, and the
      header shows search and menu icon buttons;
  - `ReaderFooter`: the scraped newspapers and *Cada noticia enlaza a su fuente original*;
  - `FrontPage`: the lead, the side column, and *Más titulares* with *Ver todas las noticias →*;
  - `LoadError`: an error notice with *Reintentar*, which calls `refetch`.
- Copy:
  - empty front page: *Aún no hay noticias. La portada se llenará cuando se lean los periódicos.*
  - load error: *No se han podido cargar las noticias. Comprueba tu conexión e inténtalo de
    nuevo.* with *Reintentar*.
- `web/playwright.config.ts`:
  - `workers: 1`, Chromium, `baseURL` set to the preview origin;
  - `webServer` starts:
    - the API: `uv run --project .. daily-trends-py`, with `ENV=test`, `PORT=<API_PORT>`,
      `MONGO_URL=mongodb://localhost:27017/daily-trends-e2e` and
      `SCRAPE_SCHEDULE_ENABLED=false`, waiting on `/status`;
    - the app: `pnpm build && pnpm preview --port 4173`, with `API_PORT`.
- `web/tests/e2e/fixtures.ts`:
  - a Playwright fixture `feeds` that empties the `feeds` collection before each test;
  - `feeds.seed(...partials)` inserts documents in the stored shape, through the `mongodb`
    driver (dev dependency), with the same `MONGO_URL`.
  - S15 extends this harness with an administrator.
- CI: job `e2e`:
  - Mongo service, uv, Node and Corepack;
  - `pnpm install --frozen-lockfile`, `pnpm exec playwright install --with-deps chromium`, then
    `pnpm e2e`;
  - the HTML report is uploaded when the job fails.

### Tests first

- [x] `front-page.test.ts`:
  - `splitFrontPage` for 0, 1, 4 and 10 feeds: 1 is a lead alone, 4 is a lead plus 3 side
    feeds and no *more*, 10 is 1 + 3 + 6;
  - `lastUpdated` picks the newest date.
- [x] `routes/index.test.tsx` (MSW, with the real router and query client):
  - loading shows skeletons;
  - 10 feeds render the lead headline as Display, 3 side feeds, 6 cards under *Más titulares*
    and *Ver todas las noticias →*;
  - 4 feeds render no *Más titulares*;
  - 1 feed renders only the lead;
  - 0 feeds render the empty state;
  - a 500 renders the error notice with *Reintentar* and no empty state, and clicking it
    requests again and renders the feeds;
  - each headline links to `/feeds/<id>`;
  - *Leer en El Mundo* opens `url` in a new tab with `rel="noopener noreferrer"`;
  - a `CMS` feed has no source link;
  - the top bar shows *Actualizado hace N min* from the newest `created_at`.
- [x] `ReaderHeader.test.tsx`:
  - the section links point at `/feeds?category=…`;
  - *Secciones* toggles `aria-expanded` and the list;
  - the landmarks `header`, `nav` and `footer` exist.
- [x] `web/tests/e2e/front-page.spec.ts`:
  - with 10 seeded scraped feeds, the lead, the side column and the grid show them in API order,
    and a source link has the seeded `url` and `target=_blank`;
  - no request leaves `localhost` while the page loads, which checks that the fonts come from
    the bundle.

### Implementation

- [x] Write the query client, the hooks, the layout components and the front page. Wire the root
  route with `QueryClientProvider` and the layout.
- [x] Add the Playwright config, the fixtures and the `e2e` CI job.
- [x] Run the web gate including `pnpm e2e` (Mongo from `docker compose up -d --wait mongo`).
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **Pulled forward from phase 4:** the header's typed links to `/feeds?category=…` need the browse
  route and its search params.
  - `src/routes/feeds.index.tsx` exists as a stub with `validateSearch: parseFeedFilters`.
  - `parseFeedFilters` (`features/feeds/feed-filters.ts`, with its tests) drops unknown
    categories and sources, and trims `q`, dropping it when blank or longer than 100.
  - Phase 4 adds the URL rewrite and the page itself.
- **Query client:**
  - `createQueryClient({ retryDelay, log })` retries a failed read once, after 500 ms in the app
    and at once in tests.
  - It never retries a 4xx `ApiError`, which phase 5 needs for 400 and 404.
  - `log` defaults to `console.error`, and tests pass a recorder.
  - `createAppRouter({ queryClient, history })` wraps the router in `QueryClientProvider`.
  - `feedKeys` only has `home` for now: the list and detail keys come with their screens.
- **Layout:** `ReaderPage` renders the header, the page's own `main` and the footer. The
  front-page masthead is the page's `h1`.
- **Mobile:**
  - The masthead sits on the left, with the search link and the menu button beside it.
  - The menu button opens the same sections list as *Secciones*.
  - The list shows the 11 categories with their marker (`CategoryMarker`, exported from
    `category-label.tsx`) and *Todas las noticias*.
  - *Buscar* leads to `/feeds`. Focusing the search box comes with phase 4.
- **Front page:**
  - The route branches on `data`, so a failed refetch keeps the feeds already shown.
  - The empty state has no action.
- **E2E harness:**
  - Ports default to 5199 for the API and 4173 for the app, and `E2E_API_PORT`, `E2E_WEB_PORT`
    and `E2E_MONGO_URL` override them.
  - The app's web server runs `vite build && vite preview`, not `pnpm build`. pnpm is not on the
    child process's PATH without `corepack enable`, and E2E does not need the type-check.
  - The front-page scenario was written after the screen. It also follows a headline to its
    page.
- **Checked by hand with screenshots:**
  - 1440 px in light against the canvas;
  - 390 px in dark with the sections open;
  - no horizontal scroll at 360 and 390 px.

## Phase 4: Browse

`/feeds` lists `GET /feed/list` with category, newspaper and search filters held in the URL, and
pages through `next_cursor`.

### Public contracts

- `web/src/routes/feeds.index.tsx`: `validateSearch` returns `{ category?: FeedCategory; source?:
  FeedSource; q?: string }`.
  - An unknown category or source is dropped.
  - `q` is trimmed, and dropped when it is blank or longer than 100 characters.
  - When the input changes, a `beforeLoad` redirect rewrites the URL with `replace: true`. For
    example, `/feeds?category=nope` becomes `/feeds`.
- `web/src/api/feeds.ts`: `useFeedList(filters)`.
  - It uses `useInfiniteQuery` with `limit=20`, keyed by the filters, so a filter change starts
    again from page 1.
  - `getNextPageParam` reads `next_cursor`.
- `web/src/lib/use-debounced-value.ts`: `useDebouncedValue<T>(value: T, delayMs: number): T`.
- `web/src/features/feeds/` components:
  - `CategoryChips`: *Todas* and the 11 categories, one pressed;
  - `SourceSelect`: *Todos*, the 5 newspapers and *Redacción*;
  - `SearchBox`: labelled *Buscar noticias*, `maxLength=100`; it applies after 300 ms or on
    Enter, and clearing it removes `q`;
  - `FilterSummary`: it names the active filters, with *Limpiar filtros*;
  - `FeedList`: rows with the time column, and *Cargar más*;
  - `FiltersPanel`: below 640 px, *Filtros* plus the count of active filters, with
    `aria-expanded`.
- Copy: the empty state is *No hay noticias de <filters>.* with *Limpiar filtros*. The error uses
  `LoadError`.

### Tests first

- [x] `use-debounced-value.test.ts`: with fake timers, the value changes once after 300 ms of
  quiet.
- [x] `routes/feeds.index.test.tsx` (MSW):
  - the first page renders 20 rows newest first, with *Hoy*, *Ayer* or the day, and the time;
  - *Cargar más* requests `cursor=<next_cursor>`, appends the rows, and disappears when
    `next_cursor` is `null`;
  - a category chip sets `?category=SPORTS` and requests with it;
  - *Todas* removes it;
  - the select sets `source`;
  - typing `ma`, `mad`, `madrid` quickly makes one request for `madrid`;
  - Enter applies at once;
  - clearing removes `q`;
  - an answer for an older query never replaces a newer one (MSW delays the older answer);
  - changing a filter after *Cargar más* starts again from page 1;
  - `?category=nope` renders unfiltered, with the URL rewritten and no `category` sent;
  - `?category=SPORTS&source=EL_MUNDO&q=madrid` pre-selects the filters and names them in the
    summary;
  - *Limpiar filtros* clears them;
  - no results show the empty state naming the filters;
  - a 500 shows `LoadError`;
  - loading shows row skeletons;
  - the *Filtros* button shows the active count.
- [x] `web/tests/e2e/browse.spec.ts`: with 25 seeded feeds across categories, sources and words,
  filtering by category, by newspaper and by a word shows only the matching ones, and *Cargar más*
  loads the second page.

### Implementation

- [x] Write the search validation, the hooks and the components. Back and forward restore the
  filters through the router.
- [x] Run the web gate including `pnpm e2e`.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **URL rewrite:**
  - The route's `search` also keeps the root's unvalidated params. TanStack Router merges them
    into the validated ones, so `category=nope` survived the validation.
  - `beforeLoad` therefore validates the raw `location.search`, and redirects with
    `replace: true` when any raw param is dropped or changed. Unknown params are dropped too.
- **`unwrap`:** it is typed on the whole result (`Promise<NonNullable<R["data"]>>`). Inferring the
  body from openapi-fetch's union added the error side's `undefined` for `/feed/list`.
- **Copy:**
  - Filters are described as words: *Noticias con “madrid” en Deportes de El Mundo*, and the
    empty state reads *No hay noticias con “ópera” en Cultura.* with *Limpiar filtros*.
  - Without filters, the empty state reads *Todavía no hay noticias.*
- **Components:**
  - The summary line and the phone's *Filtros* toggle live in the route, not in their own
    components.
  - The *Filtros* button's accessible name counts the active filters, for example
    *Filtros (2 activos)*.
  - The chips are a `fieldset` with a hidden legend *Categoría*, and the search box sits in a
    `<search>` element. These are Biome's semantic-element rules.
  - The source select offers `EL_PAIS` only when the URL already names it.
- **Search:**
  - *Buscar* in the front-page header leads to `/feeds#buscar`, which focuses the search box.
  - The box keeps the last applied search, so going back or clearing the filters updates the
    text without applying the search again.
- **Tests:**
  - `src/test/fake-feed-list.ts` is a fake `GET /feed/list`. It filters by category, source and
    whole words and pages with a cursor, it can delay answers to reorder them, and it records
    each request's query.
  - The debounce is tested with fake timers; the screen tests use real ones.
- **E2E:**
  - `browse.spec.ts` covers paging up to the last page and filtering by category, newspaper and
    a word.
  - The search for *elección* finds *elecciones* through the API's Spanish text index.
- **Checked by hand with screenshots:** 1440 px in light, and 390 px in dark with the filters
  open. There is no horizontal scroll at 360 px.

## Phase 5: Detail, not found and documentation

`/feeds/$id` shows a feed with its source panel and related feeds. Unknown feeds and routes show
a *not found* page, and the docs are updated.

### Public contracts

- `web/src/api/feeds.ts`:
  - `useFeed(id)`. A 404 or a 400 `ApiError` is not retried.
  - `useRelatedFeeds(category, excludeId)`: it requests `/feed/list?category=…&limit=4` and
    answers up to 3 feeds without `excludeId`.
- `web/src/lib/urls.ts`: `shortenArticleUrl(url: string): { host: string; path: string }`.
  - `host` has no `www.`.
  - `path` is shortened in the middle with `…` past 48 characters.
  - An unparsable URL answers itself as `host`, with an empty path.
- `web/src/routes/feeds.$id.tsx`, on the 760 px reading width:
  - the category, linked to `/feeds?category=…`, and the newspaper;
  - the Display headline, and the description as a lead-in;
  - the author, *Publicada* `<Time>`, and *Editada* when `updated_at` is set;
  - the source panel, only when there is a `url`;
  - *Más de <category>*, hidden when there are no related feeds.
- `web/src/features/feeds/NotFound.tsx`:
  - copy: *No encontramos esta noticia.* with *Volver a la portada*;
  - used for a 404, for a 400 and as the router's `notFoundComponent`.
- Docs:
  - `S00` *What the system is* mentions the web reader in `web/`;
  - `README.md`: running the API and the app together, the web commands, and `web/` in the
    project layout;
  - `AGENTS.md` *Web* section: final review;
  - `S14` and the design system: status `implemented`.

### Tests first

- [x] `urls.test.ts`: the host without `www.`, a long path shortened, a short path kept, and an
  invalid URL.
- [x] `routes/feeds.$id.test.tsx` (MSW):
  - a feed renders its fields, with *Editada* only when `updated_at` is set;
  - the source panel shows the host and the path, and *Leer en <newspaper>*;
  - a `CMS` feed has no panel;
  - the related feeds leave the current one out and show at most 3;
  - none hides *Más de…*;
  - a 404 and a 400 render *not found* with a link to `/`, and are not retried;
  - a 500 renders `LoadError`;
  - loading shows skeletons;
  - there is one `h1`.
- [x] `routes/not-found.test.tsx`: an unknown route renders the *not found* page.
- [x] `web/tests/e2e/detail.spec.ts`:
  - opening a seeded feed from the front page shows it and its related feeds of the same
    category;
  - `/feeds/<unknown uuid>` and `/feeds/nope` show the *not found* page.

### Implementation

- [x] Write the hooks, the detail route and the not-found page.
- [x] Update `S00`, `README.md`, `AGENTS.md` and the spec status.
- [x] Run the Python quality gate and the full web gate:
  `pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test`.
- [x] Check the design system's acceptance criteria by hand: the screens at 1440 px and 390 px
  against the canvas, in both themes, with no horizontal scroll at 360 px.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **Not found:**
  - The copy depends on what is missing. The detail shows *No encontramos esta noticia.*, and the
    router's `notFoundComponent` shows *No encontramos esta página.* Both link to *Volver a la
    portada*.
  - A 404 or a 400 from `GET /feed/{id}` shows it without a retry, because the query client
    never retries a 4xx (phase 3).
- **Detail:**
  - It has *← Volver a Explorar*, as in the canvas.
  - The category is a link to `/feeds?category=…`, made by wrapping `CategoryLabel` in a
    `Link`.
  - The source panel is a region named *Fuente original*.
  - The related feeds are a list of headlines with *source · time*, under the heading *Más de
    <category>*.
- **Related feeds:** `useRelatedFeeds` uses `skipToken` until the feed's category is known.
  Detail pages of the same category share the query, and each page leaves itself out with
  `select`.
- **Spec status:** the spec statuses stay *draft*. Every spec in the repository keeps that status
  once implemented, so S14 and the design system follow the convention instead of changing to
  `implemented`.
- **Docs:**
  - `S00` describes the web app under *What the system is*.
  - The README layout lists `web/`, `specs/users/` and `specs/web/`.
  - `AGENTS.md` describes the layout of `web/src`.
- **E2E:** the *not found* scenarios use no fixture. A random UUID never exists, and Mongo rejects
  an empty insert.
- **Checked by hand with screenshots:**
  - 1440 px in light and 390 px in dark match the canvas in layout and hierarchy for the three
    screens.
  - There is no horizontal scroll at 360 px on any screen, including *not found*.
  - The dark source button reads `#EDEDEF` on `#17171A`. The washed-out look in one screenshot
    was its 150 ms color transition, caught after switching themes.

## Next step

All phases are implemented. After review, commit Phase 5 and open the pull request for `feat/s14-web-reader`. S15 (the web CMS) builds on this harness and the design system.
