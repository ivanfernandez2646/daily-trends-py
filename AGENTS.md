# Agent guide

This repository is a Spec-First Python project. It is a port of a TypeScript/Node project
and keeps its hexagonal architecture with bounded contexts.

## Required workflow

1. Write or update `specs/<subdomain>/<feature>.md` (bounded context `cms`, subdomain `feeds`: `specs/feeds/S0N-*.md`, read in order from `S00`). Improvements to the ported behavior go in `specs/improvements/I0N-*.md`.
2. Run `/ai-project-create-plan` to agree public contracts and vertical phases.
3. After approving the plan, the agent creates a feature branch automatically.
4. Run `/ai-project-implement-phase`. It implements exactly one phase using TDD, then stops for review.
5. Run `/ai-project-conventional-commit` only when ready. Commits are never automatic.

`/ai-project-create-plan`, `/ai-project-implement-phase`, and `/ai-project-conventional-commit`
are user-invoked. Supporting skills under `.agents/skills/` are selected by the agent.

## Reference and scope

- The original Node project is a read-only reference in `reference/daily-trends-node/` (git-ignored). Its `.feature` files were the behavioral source of truth for the port (S00–S07).
- The port is complete and keeps the original behavior, defects included. A defect listed in `specs/improvements/README.md` is in scope only once an `I0N-*.md` spec covers it; that spec then supersedes the `S0N` behavior it changes. Do not implement items without a spec.

## Architecture

- `src/<package>/apps/<app>`: entry points (FastAPI app, jobs), the composition root (DI container),
  transport and validation (routers, Pydantic request and response schemas) and the exception
  handlers. Bounded contexts have no HTTP layer.
- `src/<package>/contexts/<context>/<subdomain>/application`: use-case orchestration.
- `src/<package>/contexts/<context>/<subdomain>/domain`: framework-free business types and rules.
- `src/<package>/contexts/<context>/<subdomain>/infrastructure`: external SDK, database and network adapters.
- `src/<package>/contexts/<context>/shared`: shared kernel for that context.

In this project: `src/daily_trends_py/apps/cms_backend` and `src/daily_trends_py/contexts/cms/{feeds,shared}`.

Application code depends on ports (`typing.Protocol`). Infrastructure adapters contain only
technology details. Domain and application code never import FastAPI, Pydantic or database drivers.
Wiring lives in one composition root per app: a [dishka](https://dishka.readthedocs.io) container
(`apps/<app>/container.py`) composed from `apps/<app>/providers/`: one provider for the shared
infrastructure and one per subdomain, so a new bounded context adds its provider, its router and
its `STARTUP_DEPENDENCIES`. Only `apps/<app>` and its tests import dishka; tests swap in fakes with
override providers. Every router uses `JsonBodyRoute`, and every error goes through
`apps/<app>/errors.py`: a new domain error picks its status by inheriting from an error kind.

MongoDB schema changes (indexes, data reshapes) are versioned migrations applied at startup;
the `ai-project-mongo-migrations` skill explains how to add one.

## Quality rules

- Python 3.14 managed with `uv`. Never use `pip` or install into the global Python.
- Strict typing: `pyright` in strict mode. No `Any` unless justified in a comment. Full parameter and
  return annotations.
- `snake_case` for functions, variables and modules, `PascalCase` for classes. Type-only imports
  and relative imports follow `ruff` defaults.
- English in code, docs, tests, errors, and commits.
- Value objects are `@dataclass(frozen=True)`; entities are `@dataclass(eq=False)`.
- Dates are timezone-aware UTC `datetime`. Never `datetime.utcnow()` or naive `datetime.now()`.
- Optional fields distinguish "absent" from `None` when the contract requires it.
- Never block the event loop; keep a strong reference to background `asyncio` tasks and log their errors.
- Test behavior first: red, green, refactor.
- Use fake classes that implement the port instead of `unittest.mock`, `AsyncMock`, or import patching.
- Use Object Mothers for expressive domain fixtures.
- Read existing code before introducing a pattern. Prefer simple functions and modules over
  speculative abstractions.
- Add comments only when they explain a non-obvious reason.
- Keep changes small, independently verifiable, and tied to an approved spec and plan phase.
- Never implement or commit on `main` or `master`.
- Never commit secrets or real credentials.

## Commands

```bash
uv sync                      # install
uv run fastapi dev           # run the API with reload
uv run daily-trends-py       # run the API on PORT (default 5000)
uv run ruff check .          # lint
uv run ruff format .         # format
uv run pyright               # type-check
uv run lint-imports          # layer and dependency contracts
uv run pytest                # tests
```

Quality gate:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run lint-imports \
  && uv run pytest
```

After each coherent slice, run lint, type-check, and the relevant test suite. Before handing off a
phase, run the full quality gate and fix errors introduced by the change.

## Web

The web app lives in `web/` (specs in `specs/web/`, its look in `specs/web/design-system.md`). It has
its own toolchain: Node from `web/.nvmrc`, pnpm pinned through `packageManager` (run
`corepack enable` once). The Python tooling never looks inside `web/`, and the web tooling never
looks outside it, except `pnpm api:generate`.

```bash
cd web
pnpm install                 # install
pnpm dev                     # the app on http://localhost:5173, proxying the API on PORT
pnpm api:generate            # after any route or schema change in the API
pnpm lint                    # Biome
pnpm typecheck               # tsc
pnpm test                    # Vitest
pnpm build                   # production build
pnpm e2e                     # Playwright: the real API and Mongo with the built app
```

Web quality gate, from `web/`:

```bash
pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test
```

- The API contract is generated: `pnpm api:generate` writes `web/openapi.json` (from
  `uv run daily-trends-py openapi`) and `web/src/api/schema.gen.ts`. Commit both. CI fails when they
  are out of date. Never edit generated files (`*.gen.ts`, `openapi.json`).
- Components never call `fetch`: they use the hooks of `src/api`, built on the typed client
  (`src/api/client.ts`). Response types come from `schema.gen.ts`, never from hand-written
  interfaces.
- Tests use MSW as a fake API that answers like the real one (`src/test/server.ts`, feed mothers
  in `src/test/`). No `vi.mock` or module mocking. A request without a handler fails the test.
- End-to-end tests (`web/tests/e2e/`) run the real API with `ENV=test` and scheduled scraping off
  against the `daily-trends-e2e` database, which each test empties and seeds through the `feeds`
  fixture. They never call `/feed/scrap`: it reads the real newspapers.
- TypeScript is `strict`. No `any` without a comment that justifies it.
- The interface is in Spanish; code, comments, tests and commits stay in English.
- Styles use the Tinta tokens, never raw colors.
