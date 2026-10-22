---
name: 's15-web-cms'
description: 'Administrators log in to the web app and manage feeds: list, scrape, create, edit and delete, with a session in sessionStorage that ends cleanly at expiry; create-admin reads the password from stdin for scripts'
spec: 'specs/web/S15-web-cms.md'
branch: 'feat/s15-web-cms'
created_at: '2026-10-22T10:00:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-22T18:00:00Z'
implemented_at: '2026-10-22T18:00:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S15 · Web CMS

## Goal

The web app gains a CMS for administrators:

- `/login`, with a session kept in `sessionStorage`, restored with `GET /auth/me`, and ended at
  `token_expires_at` or on any 401;
- `/admin`, which lists every feed with the `/feeds` filters, scrapes the front pages and deletes
  feeds;
- `/admin/feeds/new` and `/admin/feeds/$id/edit`, which create and edit feeds.

The API gains `create-admin --password-stdin`, which the E2E harness uses to create its
administrator.

## Context

- **The API contract already covers S15.** `web/openapi.json` and `schema.gen.ts` have
  `POST /auth/login`, `GET /auth/me`, `PUT`/`PATCH`/`DELETE /feed/{id}` and `GET /feed/scrap`,
  with the bearer scheme. No route or schema changes, so `pnpm api:generate` produces no diff.
  - `POST /auth/login` → `AccessTokenResponse {access_token, token_type, expires_in}`. 401 is
    `{"error": "Invalid email or password"}`.
  - `GET /auth/me` → `AdminSessionResponse {id, email, created_at, token_expires_at}`.
  - `GET /feed/scrap` → `FeedResponse[]`, the feeds stored by this run. N is its length.
  - `PUT /feed/{id}` → 201 `FeedResponse`, or 409 `Feed with id <…> already exists`.
  - `PATCH /feed/{id}` takes `UpdateFeedRequest` (absent keeps, `null` clears the description)
    → 200, or 404.
  - `DELETE /feed/{id}` → 204 with no body, or 404.
  - Every error is `{"error": "…"}`. A 400 joins the problems as `loc: msg; …`.
- **The web app today:**
  - `api/client.ts` has no middleware, and `unwrap` throws on an empty body, so the 204 needs
    its own helper.
  - `api/feeds.ts` has only queries. Every key starts with `feedKeys.all`.
  - The root is `createRootRoute`, with no router context, and the query client reaches the app
    only through `Wrap`.
  - `components/ui` has `Button` (with `destructive`), `IconButton`, `Field`, `Select`, `Chip`,
    `Notice` and `CategoryMarker`. There is no Dialog, Toast, Textarea or table.
  - The `radix-ui` meta-package already includes AlertDialog and Toast.
  - No form library: the forms are plain React state.
  - Neither reader header has *Acceder*. S14 left it to S15.
- **The CLI:**
  - `main.py` parses `create-admin [--email]` with argparse.
  - `cli.create_admin(settings, *, email, prompt, secret_prompt, migrations)` asks for the
    password twice.
  - `tests/apps/cms_backend/test_cli.py` (integration, real Mongo) fakes the prompts with plain
    functions and checks the output with `capsys`.
- **The E2E harness:**
  - `playwright.config.ts` starts one API (`ENV=test`, `SCRAPE_SCHEDULE_ENABLED=false`, port
    5199) and one `vite preview` (port 4173), whose proxy reads `API_PORT`.
  - The token TTL is fixed when the API starts.
- **Agreed:**
  - **Phases:** four vertical phases.
  - **Expiry end to end:** a second API with `AUTH_TOKEN_TTL_SECONDS=10` and its own preview, in a
    Playwright project `session-expiry`.
  - **Leaving the form with unsaved changes:** an in-app `ConfirmDialog` through `useBlocker`.
    The browser's `beforeunload` prompt covers closing or reloading the tab.
- **Decisions where the spec is silent or the code differs:**
  - **The login response has no `token_expires_at`.** After a 200 the app stores the token and
    calls `GET /auth/me`, the same path as a restore, so the email and the expiry always come from
    the server. If `/auth/me` fails, the token is forgotten and the login shows the generic error.
  - **`--password-stdin` requires `--email`.** Both would otherwise read stdin. Without it,
    argparse exits 2 with `--password-stdin requires --email`.
  - **The redirect rule:**
    - accepted only when it starts with `/` and not with `//` or `/\`, because browsers read `/\`
      as `//`;
    - anything else, and a missing value, goes to `/admin`.
  - **A 401 on start only forgets the token.** A reader on `/` stays there.
  - **The session ends with a redirect only on `/admin` pages.** On a reader page the token is
    forgotten and the header shows *Acceder* again. The point of the redirect is that a write never
    fails, and the reader makes none.
  - **The redirect at expiry ignores the leave blocker** (`ignoreBlocker: true`), as the spec's
    edge case requires.
  - **The token travels in an openapi-fetch middleware.** It adds `Authorization: Bearer` only
    while a token is held. A 401 to a request that carried it ends the session.
  - **Notices after a navigation are toasts at the bottom** (design system): `Toaster` and
    `useToast()` on Radix Toast, with the `Notice` look. Errors that block a form stay inline.
  - **Copy the spec does not give:**
    - validation: *Escribe un titular*, *Escribe el autor*, *Elige una categoría*, and for login
      *Escribe tu email* and *Escribe tu contraseña*;
    - the scrape result for one feed: *Portadas actualizadas: 1 noticia nueva*;
    - action errors: *No se pudo borrar la noticia*, *No se pudieron actualizar las portadas*, and
      for login *No se pudo iniciar sesión*. Each shows the API message as detail, and a network
      error shows no detail;
    - the leave dialog: *¿Salir sin guardar?*, *Los cambios que no has guardado se perderán.*,
      with *Seguir editando* and *Salir*.
  - **The create form's id** is generated once per form with `crypto.randomUUID()`. It is
    generated again after a 409, so trying again can succeed.
  - **Trimming:** values are trimmed before they are checked, compared and sent.
    - Create omits a blank description.
    - Edit sends `description: null` only when a description existed and is now blank.
  - **Forms use `noValidate`,** so the app's Spanish messages replace the browser's.
  - **The preview card** is a `FeedCard` built from the draft (`source: "CMS"`, `created_at` now)
    with `linked={false}`, because the feed does not exist yet.
  - **The login brand panel** reuses the masthead and its tagline, as in the canvas.

## Phases

## Phase 1: Session, login and the admin shell

`create-admin` reads the password from stdin. Administrators log in at `/login`, the session
survives a reload and ends at expiry or on a 401, `/admin` requires a session and shows the CMS
layout, and the reader header links to the CMS.

### Public contracts

- CLI: `uv run daily-trends-py create-admin --email <email> --password-stdin`.
  - It reads one line from stdin, removes its line ending, and asks for no repetition. The rest is
    S11: the same validation, messages and exit codes, and the password is never printed.
  - `--password-stdin` without `--email` → argparse error, exit 2.
  - `--help` describes it as "Read the password from the first line of standard input."
- `cli.create_admin(settings, *, email, prompt, secret_prompt, migrations, password_from: TextIO
  | None = None)`. With `password_from`, `secret_prompt` is not called.
- `web/src/api/client.ts`:
  - `unwrapEmpty(request): Promise<void>`, which throws `ApiError` for a non-2xx answer;
  - `api.use(authMiddleware(session))`.
- `web/src/api/auth.ts`:
  - `logIn(email, password): Promise<string>`, the token;
  - `fetchAdminSession(token): Promise<AdminSessionResponse>`.
- `web/src/api/types.ts`: aliases `AdminSessionResponse`, `CreateFeedRequest` and
  `UpdateFeedRequest`.
- `web/src/features/session/session.ts`: `createSession({ storage, now? })` answers a `Session`:
  - `status(): "anonymous" | "restoring" | "active"` and `admin(): { email; expiresAt } | undefined`;
  - `token(): string | undefined`;
  - `restore(): Promise<void>`, idempotent: with a stored token it calls `/auth/me`, where 200
    activates the session and 401 forgets the token;
  - `start(token): Promise<void>`: it stores the token, then restores;
  - `end(reason: "logout" | "expired")` and `subscribe(listener)`;
  - a timer that ends the session with `"expired"` at `token_expires_at`. Delays above
    `2^31 − 1` ms are chained.
- `web/src/features/session/redirect.ts`: `safeRedirect(value: unknown): string`.
- `web/src/features/session/use-session.ts`: `useSession()`, through `useSyncExternalStore`.
- Router:
  - `__root.tsx` becomes `createRootRouteWithContext<{ session: Session }>()`;
  - `createAppRouter({ queryClient, session, history })`;
  - `main.tsx` creates the session on `sessionStorage` and calls `restore()` at start.
- `web/src/lib/dates.ts`: `formatClock(iso): string`, `HH:MM` in `Europe/Madrid`.
- Routes:
  - `login.tsx`: `validateSearch` → `{ redirect?: string }`.
    - `beforeLoad` awaits `restore()` and sends an active session to `/admin`.
    - The page has *Email*, *Contraseña* and *Entrar*.
    - 401 → *Email o contraseña incorrectos*.
    - Success → `safeRedirect(redirect)`.
  - `admin.tsx`, the guard and the layout:
    - `beforeLoad` awaits `restore()`; without a session it redirects to
      `/login?redirect=<location.href>`;
    - the component subscribes to `"expired"` and navigates to `/login?redirect=<current href>`
      with `ignoreBlocker: true`.
  - `admin.index.tsx`: for now the title *Noticias*.
- `web/src/features/admin/admin-layout.tsx`: the 240 px side menu, stacked above the content on
  narrow screens:
  - the brand and *CMS*;
  - *Noticias* (`/admin`) and *Ver el sitio* (`/`);
  - the email, *Sesión hasta las HH:MM* and *Cerrar sesión*, which ends with `"logout"` and goes
    to `/`.
- `ReaderHeader`, both variants: *Acceder* (`/login`) without an active session, *CMS* (`/admin`)
  with one.
- E2E:
  - `web/tests/e2e/environment.ts`: `ADMIN_EMAIL`, `ADMIN_PASSWORD` (test values), plus
    `EXPIRY_API_PORT` and `EXPIRY_WEB_PORT`;
  - `web/tests/e2e/global-setup.ts`: it empties `users` and runs `create-admin --email …
    --password-stdin` against the E2E database;
  - `web/tests/e2e/admin.ts`: `logIn(page, { email?, password? })`;
  - `playwright.config.ts`:
    - project `default` (the existing specs and the CMS specs);
    - project `session-expiry` (`*.expiry.spec.ts`), with its own API
      (`AUTH_TOKEN_TTL_SECONDS=10`, same Mongo) and its own preview proxying to it.

### Tests first

- [x] `tests/apps/cms_backend/test_cli.py`:
  - with `password_from=io.StringIO("<password>\n")` and `secret_prompt=no_prompt`, the admin is
    created, exit 0, and the password is not in stdout or stderr;
  - a short password, an invalid email and a duplicate exit 1 with the S11 messages;
  - `\r\n` and a missing final newline are both read correctly;
  - the subprocess test: `create-admin --email … --password-stdin` with one line on stdin exits 0;
  - `--password-stdin` without `--email` exits 2.
- [x] `web/src/features/session/redirect.test.ts`: `/admin/feeds/x/edit?q=a` is kept. `//evil`,
  `/\evil`, `https://evil.example`, `admin`, an empty value and a non-string give `/admin`.
- [x] `web/src/features/session/session.test.ts` (MSW, fake timers for `Date` and `setTimeout`):
  - no stored token → `anonymous`, with no request;
  - a stored token and `/auth/me` 200 → `active`, with email and expiry;
  - `/auth/me` 401 → the token is forgotten, `anonymous`;
  - the session ends with `"expired"` at `token_expires_at`, not before;
  - `restore()` called twice makes one request.
- [x] `web/src/api/client.test.ts`:
  - the middleware sends `Authorization: Bearer <token>` only while a token is held;
  - a 401 with the token ends the session with `"expired"`;
  - `unwrapEmpty` resolves on 204 and throws `ApiError` on 404.
- [x] `web/src/routes/login.test.tsx` (MSW):
  - wrong credentials → *Email o contraseña incorrectos*;
  - empty fields → the two Spanish messages, with no request;
  - success stores the token in `sessionStorage` and goes to `redirect`;
  - an unsafe or missing `redirect` goes to `/admin`;
  - an active session that opens `/login` goes to `/admin`.
- [x] `web/src/routes/admin.test.tsx` (MSW):
  - no session → `/login?redirect=%2Fadmin…`;
  - a stored token restored by `/auth/me` renders the layout with the email and *Sesión hasta
    las HH:MM*;
  - at `token_expires_at` → `/login` with the current page as `redirect`;
  - *Cerrar sesión* forgets the token and goes to `/`.
- [x] `web/src/features/feeds/reader-header.test.tsx`: *Acceder* without a session, *CMS* with
  one, in both variants.
- [x] `web/src/lib/dates.test.ts`: `formatClock`, including across the DST change.
- [x] `web/tests/e2e/session.spec.ts`:
  - wrong credentials show the error;
  - the right ones reach `/admin`;
  - `/admin` without a session goes to `/login` and back after logging in.
- [x] `web/tests/e2e/session.expiry.spec.ts`: after logging in on `/admin?q=madrid`, the expiry
  sends the user to `/login`, and logging in again returns to `/admin?q=madrid`.

### Implementation

- [x] Add `--password-stdin` and `password_from`.
- [x] Add the session, the middleware, the router context, the routes, the layout and the
  header link. `src/test/setup.ts` clears `sessionStorage` after each test.
- [x] Add `src/test/fake-auth.ts`: it stores a token and installs `/auth/me` with a given
  expiry, recording the `Authorization` headers. `renderRoute` builds a session on
  `sessionStorage`.
- [x] Add the global setup, the `logIn` helper and the `session-expiry` project. Both projects
  run in CI's `e2e` job.
- [x] Run the Python quality gate and the web gate including `pnpm e2e`.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **CLI:**
  - `password_from` reads one line and removes `\r\n` or `\n`. Further lines are ignored, and
    empty input is an empty password, so S11's length message applies.
  - The subprocess tests share a `run_entry_point` helper.
  - The help of `create-admin` now mentions `--password-stdin`.
- **Session:**
  - The token is kept under `daily-trends.access-token`.
  - `Session` also has `onEnd(listener)`, which the admin route uses to tell an expiry from a
    logout. `subscribe` only says that the state changed.
  - `state()` answers `{ status, admin? }` instead of separate `status()` and `admin()`, because
    `useSyncExternalStore` needs one stable snapshot.
  - `token()` is defined only while the session is active.
  - Restoring forgets the token only on a 401. Any other failure leaves the session anonymous
    for this page load and keeps the token, so a reload tries again. A failed `start` always
    forgets it.
  - `fetchAdmin` is injectable, and the unit tests pass a fake with fake timers instead of MSW.
- **Middleware:**
  - `sendAccessToken(holder)` lives in `api/client.ts` and answers its own `eject`.
  - It depends on a two-method holder, not on `features/session`, so `api/` does not import
    `features/`.
  - It never replaces an `Authorization` header already set, which `/auth/me` sets for the
    token being restored.
  - Only a 401 to a request carrying the session's own token ends the session.
- **React:**
  - `features/session/session-context.tsx` has `SessionProvider`, `useSession()` and
    `useSessionState()`, instead of `use-session.ts`.
  - The router wraps the app in it, and the session also travels in the router context for
    `beforeLoad`.
- **Tests:**
  - `renderRoute` builds the session on `sessionStorage`, connects the middleware until the test
    ends (`onTestFinished`), and restores it as `main.tsx` does.
  - `renderWithRouter` takes an optional `session`.
  - `src/test/fake-auth.ts` fakes `/auth/login` and `/auth/me` with the tokens it issues.
  - The Playwright project for the existing specs keeps its name `chromium`, instead of `default`.
- **E2E:**
  - Playwright starts the web servers in order, then runs the global setup.
  - The expiry preview (`vite preview` on 4174) therefore serves the build of the first one, and
    the API has applied its migrations before `create-admin` runs.
  - The test administrator is `admin@example.com`, with the password `e2e-admin-password`.
  - CI's `e2e` job needs no change: `pnpm e2e` runs both projects.
- **Layout:**
  - On wide screens the login page shows the brand panel on `paper` next to the form card on
    `canvas`. Narrow screens show only the card.
  - The CMS side menu is an `aside` named *Menú del CMS*.
  - Not yet checked by hand at 1440 px and 390 px: phase 4 covers that, with the other screens.

## Phase 2: Feed list, scraping and deleting

`/admin` lists every feed in a table with the `/feeds` filters and paging, refreshes the front
pages, and deletes a feed after a confirmation.

### Public contracts

- `web/src/api/feeds.ts`, mutations that never retry and invalidate `feedKeys.all` on success:
  - `useScrapeFeeds()` → `FeedResponse[]`;
  - `useDeleteFeed()`: it treats a 404 like a 204 and removes `feedKeys.detail(id)`.
- `web/src/features/feeds/feed-filters.ts`: `rewriteInvalidFilters(to)`, the `beforeLoad` of
  `/feeds` extracted so that `/admin` shares it.
- `web/src/components/ui/`:
  - `ConfirmDialog({ open, title, description, confirmLabel, cancelLabel, destructive, onConfirm,
    onOpenChange })` on Radix AlertDialog, with a 16 px radius, the system's one shadow, focus
    trapped and Escape closing it;
  - `Toaster` (in the root) and `useToast().show({ tone, message, detail? })` on Radix Toast,
    shown at the bottom in the `Notice` look.
- `admin.index.tsx`:
  - `validateSearch: parseFeedFilters`, with the same rewrite;
  - the title *Noticias*, with *Actualizar portadas* (secondary) and *Nueva noticia* (primary,
    disabled until phase 3);
  - the filters: `CategoryChips`, `SourceSelect` and `SearchBox`.
- `web/src/features/admin/feeds-table.tsx`:
  - a table in a horizontally scrollable `surface` panel, with the columns *Titular*,
    *Periódico*, *Categoría* and *Fecha*;
  - the headline links to `/feeds/$id`;
  - *Editar* and *Borrar* are `IconButton`s labelled *Editar «title»* and *Borrar «title»*;
  - *Cargar más* follows `next_cursor`.
- `web/src/features/admin/delete-feed-dialog.tsx`: *¿Borrar esta noticia?*, the title, and *Esta
  acción no se puede deshacer.*, with *Cancelar* and *Borrar* (destructive).
- Copy:
  - the scrape button reads *Actualizando…* and is disabled while it runs;
  - the result reads *Portadas actualizadas: N noticias nuevas*, *… 1 noticia nueva* or *No hay
    noticias nuevas*;
  - errors: *No se pudieron actualizar las portadas* and *No se pudo borrar la noticia*, with
    the API message as detail;
  - after a delete: *Noticia borrada*;
  - the empty state follows `/feeds`.

### Tests first

- [x] `confirm-dialog.test.tsx`:
  - role `alertdialog` with its name;
  - focus moves into it;
  - Escape and *Cancelar* close it without confirming;
  - the confirm button is destructive.
- [x] `toaster.test.tsx`: a success toast has role `status` and an error toast `alert`, with the
  detail.
- [x] `routes/admin.index.test.tsx` (MSW, active session):
  - the first 20 feeds in the table, and *Cargar más* appends the next page;
  - the filters set the URL and the request, and invalid params are rewritten;
  - each headline links to `/feeds/<id>`, and the icon buttons have their accessible names;
  - scrape: *Actualizando…* and disabled while the request is pending, then *Portadas
    actualizadas: 3 noticias nuevas*, *1 noticia nueva* and *No hay noticias nuevas*. The list is
    requested again. A 500 shows the error with its detail;
  - delete: the dialog shows the title, *Cancelar* sends nothing, and confirming with 204 or with
    404 removes the row and shows *Noticia borrada*. A 500 keeps the row and shows the error;
  - a 401 from any write sends the user to `/login` with `redirect`;
  - every write request carries `Authorization`, and none is retried.
- [x] `web/tests/e2e/admin-list.spec.ts`: with seeded feeds, filtering by category shows only
  those feeds, and deleting a seeded feed from the table removes it from the table and from
  `/feeds`.

### Implementation

- [x] Add the components, the mutations, the table and the screen. The existing filter
  components are reused as they are.
- [x] Run the web gate including `pnpm e2e`.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **Toasts:**
  - `ToastProvider` and `useToast()` live in `components/ui/toaster.tsx`, built without Radix
    Toast. Radix announces each toast through a second, hidden live region, which would duplicate
    the `status`/`alert` roles that tests and screen readers rely on.
  - The notices sit in a region named *Avisos* at the bottom and reuse `Notice`.
  - A success hides after 5 s. An error stays until *Cerrar aviso*, so it can be read.
  - The provider sits in the router's `Wrap`, under the session and the query client.
- **ConfirmDialog:**
  - Radix only gives focus back to its own trigger. The dialog opens from table buttons, so it
    remembers the element focused when it opened and focuses it again on close.
  - Confirming does not close it, so a pending state and an error can show inside.
  - The delete error stays inline in the dialog rather than in a toast, so trying again is one
    click away.
- **The filter rewrite:** `filtersToRewrite(search)` answers the filters to rewrite to, or
  `undefined`, instead of `rewriteInvalidFilters(to)`, because a typed `redirect` needs a literal
  route. `/feeds` and `/admin` both use it.
- **Mutations:**
  - `useDeleteFeed` removes the feed from every cached list page at once, then invalidates
    `feedKeys.all`.
  - Neither mutation shows its own error for a 401 (`isSessionEnd`), because the session ends and
    the login page takes over.
- **Copy:** the table's date column reads *Hoy, 11:00*, using the time column of `/feeds`, with
  the full date as its `title`.
- **Placeholders until later phases:** *Nueva noticia* is disabled until phase 3, and *Editar* in
  each row until phase 4. Their typed links need the routes those phases add.
- **Tests:**
  - While the dialog is open, Radix hides the rest of the page from assistive technology. The
    failing-delete test therefore cancels the dialog before checking the row is still there.
  - `src/test/fake-feed-writes.ts` has `fakeDeleteFeed(feeds)`. It shares the array of
    `fakeFeedList`, so a deleted feed leaves the list.
- **E2E:**
  - `tests/e2e/admin.ts` gains `openAsAdmin(page, path)`.
  - `admin-list.spec.ts` covers the category filter and a delete, and then checks that `/feeds`
    no longer lists the feed.

## Phase 3: Create a feed

`/admin/feeds/new` creates a `CMS` feed with checked fields and a live preview.

### Public contracts

- `web/src/api/feeds.ts`: `useCreateFeed()`, which sends `PUT /feed/{id}` with
  `CreateFeedRequest`, never retries, and invalidates `feedKeys.all`.
- `web/src/components/ui/field.tsx`: `TextareaField`, with the same label and error rules as
  `Field`.
- `web/src/features/admin/`:
  - `CategoryPicker`: a `fieldset` *Categoría* with one `Chip` per category and its
    `CategoryMarker`, one pressed, and the error below;
  - `feed-form.ts`, the pure helpers:
    - `validateFeedForm(values): FeedFormErrors`;
    - `toCreateRequest(values): CreateFeedRequest`;
    - `toUpdateRequest(original, values): UpdateFeedRequest` (phase 4);
  - `FeedForm({ mode: "create" | "edit", … })`: the title, description (optional), author and
    category, and the preview *Así se verá en la portada*, a `FeedCard` with `linked={false}`;
  - `FeedCard` gets an optional `linked` prop, default `true`.
- `admin.feeds.new.tsx`:
  - the title *Nueva noticia*, with *Crear noticia* and *Cancelar*;
  - 201 → `/admin` with the toast *Noticia creada*;
  - 409, another 400 or a 500 → the inline error *No se pudo guardar la noticia* with the API
    message, keeping the values. A new id is generated after a 409.
- *Nueva noticia* on `/admin` is enabled and links here.

### Tests first

- [x] `feed-form.test.ts`: blank (whitespace) title and author and a missing category give their
  messages; values are trimmed; a blank description is omitted.
- [x] `routes/admin.feeds.new.test.tsx` (MSW, active session):
  - submitting empty shows the three messages and sends nothing;
  - the preview shows the typed title, description, category and *Redacción*;
  - the request is `PUT /feed/<uuid>` with the trimmed body;
  - 201 → `/admin` with *Noticia creada*;
  - 409 → the error, the values kept, and the next submit uses another id;
  - 500 → the error with its detail;
  - the request is not retried.
- [x] `category-picker.test.tsx`: each chip has its marker, one is pressed, and the error is
  linked.
- [x] `web/tests/e2e/admin-create.spec.ts`: an administrator creates a feed, sees it in
  `/admin`, and finds it on `/feeds` filtered by its category.

### Implementation

- [x] Add the helpers, the components and the route.
- [x] Run the web gate including `pnpm e2e`.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **Files:**
  - The pure helpers live in `features/admin/feed-form-values.ts`, not `feed-form.ts`, so the
    component file can be `feed-form.tsx`, matching what it exports.
  - The helpers also export `EMPTY_FEED_FORM` and `previewFeed(values, base)`. The preview shows
    *Titular de la noticia*, *Autor* and `OTHER` while those fields are blank. Phase 4 builds the
    preview from the stored feed.
- **FeedForm:**
  - It has no `mode` yet. It takes the values, errors, preview, submit label and an `error` node.
  - Phase 4 adds the read-only fields and *Borrar* where it needs them.
  - The submit button reads *Guardando…* while pending, and *Cancelar* is a link to `/admin`.
- **Validation:** errors show after the first submit and then follow each change, so a fixed
  field loses its message at once.
- **`SaveError`** is shared with phase 4. It shows *No se pudo guardar la noticia* with the API
  message for an `ApiError`, no detail for a network error, and nothing for a 401.
- **Components:**
  - `Field` and `TextareaField` share a private `Labelled` wrapper for the label, the error and
    `aria-describedby`.
  - `CategoryPicker` keeps the chosen category when it is pressed again.
- **Tests:**
  - `fakeCreateFeed({ taken })` answers 409 to the first `taken` requests, as a collision would,
    and 201 with a `CMS` feed otherwise.
  - The E2E scenario asks for the `feeds` fixture only to start from an empty collection, because
    an empty `seed()` is an empty `insertMany`, which Mongo rejects.

## Phase 4: Edit a feed, and docs

`/admin/feeds/$id/edit` edits any feed, scraped ones included, sends only what changed, guards
unsaved changes, and deletes from the form. The README explains the CMS.

### Public contracts

- `web/src/api/feeds.ts`:
  - `useUpdateFeed()`, which sends `PATCH /feed/{id}` with `UpdateFeedRequest`, never retries,
    and invalidates `feedKeys.all`;
  - the edit form reads the feed with `useFeed(id)`, refetching on mount, so it loads fresh after
    a new login.
- `admin.feeds.$id.edit.tsx`:
  - `FeedForm` in `edit` mode, prefilled;
  - the author, newspaper and original link read-only, with *El autor, el periódico y el enlace
    no se pueden cambiar*;
  - *Guardar cambios* is disabled while nothing changed;
  - 200 → `/admin` with *Cambios guardados*;
  - a 404 on load or on save → the toast *Esta noticia ya no existe*, and back to `/admin`;
  - other errors → inline *No se pudo guardar la noticia* with the detail;
  - *Borrar* opens the delete dialog of phase 2; 204 or 404 → `/admin` with *Noticia borrada*;
  - `useBlocker` with `ConfirmDialog` (*¿Salir sin guardar?*) while the form is dirty, plus
    `beforeunload`. Saving and deleting do not ask.
- Docs:
  - `README.md`: *Administrators* uses `--password-stdin` for scripts, and *Web app* explains
    logging in at `/login` and the CMS;
  - `AGENTS.md`: the *Web* layout mentions `features/session/` and `features/admin/`;
  - S00 already lists S15.

### Tests first

- [x] `feed-form.test.ts`: `toUpdateRequest` sends only the changed fields. Emptying an existing
  description sends `null`, and an unchanged blank description sends nothing.
- [x] `routes/admin.feeds.$id.edit.test.tsx` (MSW, active session):
  - the form is prefilled, and a scraped feed shows its author, newspaper and link read-only;
  - *Guardar cambios* is disabled until something changes, and again after the change is undone;
  - changing the title and category sends exactly those two fields;
  - 200 → `/admin` with *Cambios guardados*;
  - a 404 on load and a 404 on save → *Esta noticia ya no existe* and `/admin`;
  - a 500 → the inline error, with the values kept;
  - leaving dirty asks *¿Salir sin guardar?*: *Seguir editando* stays, *Salir* leaves; leaving
    clean does not ask;
  - the session expiring while the form is dirty goes to `/login` without asking, and logging in
    returns to the form, which requests the feed again;
  - delete from the form → `/admin` with *Noticia borrada*.
- [x] `web/tests/e2e/admin-edit.spec.ts`: an administrator creates a feed, edits its title and
  category, sees the change on `/feeds/<id>`, deletes it from the form, and it is gone from
  `/feeds`.

### Implementation

- [x] Add the update mutation, the edit route and the blocker. Update `README.md` and `AGENTS.md`.
- [x] Run the Python quality gate and the full web gate:
  `pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test`.
- [x] Check the design system's acceptance criteria by hand:
  - `/login`, `/admin`, the create form and the edit form at 1440 px and 390 px, in both themes,
    against the canvas;
  - no horizontal page scroll at 360 px; the table scrolls inside its panel.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Implementation notes

- **Helpers:**
  - `formFromFeed(feed)` and `toUpdateRequest(original, values)` live in `feed-form-values.ts`.
  - Unchanged means equal after trimming, so trailing spaces alone never enable *Guardar
    cambios*.
- **FeedForm:**
  - The `mode: "edit"` props carry `feed`, `changed` and `onDelete`.
  - In edit mode the author is not a field. A `fieldset` named *No se puede cambiar* shows the
    author, the newspaper and the shortened link, which opens in a new tab, or *Sin enlace*, with
    the spec's note.
  - *Borrar noticia* is a danger-colored link button at the end of the actions.
- **Loading:**
  - `useFeedForEditing(id)` refetches on mount, and the form appears only once
    `isFetchedAfterMount`, so it never starts from a cached copy.
  - A 404, or a 400 for an id that is not a UUID, shows the toast *Esta noticia ya no existe* and
    returns to `/admin`.
- **Leaving:**
  - Saving, deleting and a missing feed leave with `ignoreBlocker: true`.
  - `useBlocker` runs with `withResolver` and `enableBeforeUnload` while there are changes.
  - `ConfirmDialog` gained `cancelLabel` for *Seguir editando*.
  - After a delete the dialog shows *Noticia borrada* itself, so the form leaves without a second
    toast.
- **Hand checks:**
  - The screenshots covered `/login`, `/admin`, the create form, the edit form and the delete
    dialog, at 1440 px and 390 px, in both themes.
  - They found two defects, both fixed:
    - At 390 px and 360 px `/admin` scrolled sideways: the table's visually hidden *Acciones*
      title is absolutely positioned and escaped the scroll panel. The panel is now `relative`.
      `admin-list.spec.ts` checks that the page does not scroll sideways at 360 px.
    - In dark mode the dialog overlay brightened the page instead of dimming it. It used
      `bg-ink/40`, and ink is light in that theme. A new `--overlay` token defines it for both
      themes.
  - Nothing else differed in layout or hierarchy.
- **Docs:**
  - The README shows `--password-stdin` with `printf`, explains logging in to the CMS and its
    session, and describes the second API and app the E2E run starts.
  - `AGENTS.md` names `feeds/`, `admin/` and `session/` under `features/`.
- **E2E:** the edit scenario uses the reader's headline link with `exact: true`, because
  Playwright matches names by substring and *Editar «…»* matches too. It checks toasts inside the
  *Avisos* region, where two can show at once.

## Next step

All phases are implemented. After review, commit Phase 4 and open the pull request for
`feat/s15-web-cms`.
