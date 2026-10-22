# Web app

The reader and the CMS of daily-trends ([S14](../specs/web/S14-web-reader.md),
[S15](../specs/web/S15-web-cms.md), with the [design system](../specs/web/design-system.md)): Vite,
React and TypeScript, with types generated from the API's OpenAPI document. The interface is in
Spanish.

## Run it

Requirements: Node 24 (`.nvmrc`) and pnpm through Corepack. Run the API at the same time (see the
[repository README](../README.md#getting-started)).

```bash
corepack enable                   # once: provides the pnpm version pinned in package.json
pnpm install
pnpm dev                          # http://localhost:5173
```

In development the app proxies `/feed/…`, `/auth/…` and `/status` to `http://localhost:<PORT>`, with
`PORT` from the repository's `.env` (default `5000`), so the browser talks to a single origin.
`VITE_API_BASE_URL` sets the API origin for a build; production sets it in `render.yaml` (see
[Deployment](../docs/deployment.md)).

To manage feeds, create an administrator (see
[Administrators](../docs/configuration.md#administrators)) and open *Acceder* in the header, or
`/login`. The CMS at `/admin` lists every feed, refreshes the front pages, and creates, edits and
deletes feeds. The session is kept in the tab (`sessionStorage`): it survives a reload, and ends
when the tab is closed, when the token expires (`AUTH_TOKEN_TTL_SECONDS`) or with *Cerrar sesión*.

## API contract

After changing a route or a schema in the API, regenerate the contract and commit it:

```bash
pnpm api:generate                 # runs `uv run daily-trends-py openapi` and regenerates the types
```

`uv run daily-trends-py openapi` prints the OpenAPI document without starting the API or reading
any configuration. CI fails when `openapi.json` or `src/api/schema.gen.ts` are out of date.

## Tests

```bash
pnpm lint                         # Biome
pnpm typecheck                    # tsc
pnpm test                         # Vitest, with MSW as a fake API
pnpm e2e                          # Playwright against the real API and MongoDB
```

End-to-end tests need MongoDB (`docker compose up -d --wait mongo`) and Chromium
(`pnpm exec playwright install chromium`, once). `pnpm e2e` starts the API on port 5199 against the
`daily-trends-e2e` database, with scheduled scraping off, and the built app on port 4173. It also
starts a second API on port 5198 whose tokens expire after 10 seconds, with the app on port 4174,
for the expired session scenario, and creates a test administrator with `create-admin
--password-stdin`.

Quality gate:

```bash
pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test
```
