# Agent guide

This repository is a Spec-First Python project. It is a port of a TypeScript/Node project
and keeps its hexagonal architecture with bounded contexts.

## Required workflow

1. Write or update `specs/<context>/<feature>.md` (bounded context `feeds`: `specs/feeds/S0N-*.md`, read in order from `S00`).
2. Run `/ai-project-create-plan` to agree public contracts and vertical phases.
3. After approving the plan, the agent creates a feature branch automatically.
4. Run `/ai-project-implement-phase`. It implements exactly one phase using TDD, then stops for review.
5. Run `/ai-project-conventional-commit` only when ready. Commits are never automatic.

`/ai-project-create-plan`, `/ai-project-implement-phase`, and `/ai-project-conventional-commit`
are user-invoked. Supporting skills under `.agents/skills/` are selected by the agent.

## Reference and scope

- The original Node project is a read-only reference in `reference/daily-trends-node/` (git-ignored). Its `.feature` files are the behavioral source of truth.
- The port keeps current behavior, defects included. Anything listed in `specs/improvements/` is out of scope: do not implement it.

## Architecture

- `src/<package>/apps/<app>`: entry points (FastAPI app, jobs) and the composition root.
- `src/<package>/contexts/<context>/<subdomain>/api`: transport and validation (routers, Pydantic schemas).
- `src/<package>/contexts/<context>/<subdomain>/application`: use-case orchestration.
- `src/<package>/contexts/<context>/<subdomain>/domain`: framework-free business types and rules.
- `src/<package>/contexts/<context>/<subdomain>/infrastructure`: external SDK, database and network adapters.
- `src/<package>/contexts/<context>/shared`: shared kernel for that context.

Application code depends on ports (`typing.Protocol`). Infrastructure adapters contain only
technology details. Domain and application code never import FastAPI, Pydantic or database drivers.
Wiring lives in one composition root; there is no DI container.

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
uv run fastapi dev           # run the API (once the app exists)
uv run ruff check .          # lint
uv run ruff format .         # format
uv run pyright               # type-check
uv run pytest                # tests
```

Quality gate:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```

After each coherent slice, run lint, type-check, and the relevant test suite. Before handing off a
phase, run the full quality gate and fix errors introduced by the change.
