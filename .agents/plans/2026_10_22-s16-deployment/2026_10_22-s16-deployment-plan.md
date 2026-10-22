---
name: 's16-deployment'
description: 'The API, the web app and MongoDB run on Render and Atlas free plans, described in render.yaml and a keep-alive workflow, deployed by a merge to main that passes CI'
spec: 'specs/ops/S16-deployment.md'
branch: 'chore/s16-api-on-render'
branches:
  phase_1: 'chore/s16-api-on-render'
  phase_2: 'chore/s16-keep-alive'
  phase_3: 'chore/s16-web-app'
created_at: '2026-10-22T09:53:00Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-22T10:20:00Z'
---

# S16 · Deployment

## Goal

The API runs as a free Render web service in Frankfurt against a free Atlas cluster in
`eu-central-1`, a GitHub Actions workflow keeps it awake, and the web app is a free Render static
site that calls it. Everything Render needs is in `render.yaml`, so a merge to `main` that passes CI
deploys what changed. The application does not change.

## Context

- **Already true, no code change needed:**
  - `GET /status` (`apps/cms_backend/routes/status.py`) answers 200 without reading Mongo.
  - The lifespan runs the migrations before taking traffic, then `FeedScrapeScheduler.start()`
    creates a background task, so the startup scrape does not delay the health check.
  - `_serve` calls `uvicorn.run(app, host="0.0.0.0", port=settings.port)`. uvicorn has
    `proxy_headers=True` by default and, when `forwarded_allow_ips` is not passed, reads
    `FORWARDED_ALLOW_IPS` from the environment, so the variable in `render.yaml` is enough.
  - `Settings` requires `MONGO_URL` and `AUTH_SECRET_KEY` (32 characters or more) when
    `ENV=production`, and reads `PORT`. Render's `generateValue` is a base64 256-bit value
    (44 characters).
  - CORS allows any origin and any header.
  - `web/src/api/client.ts` uses `import.meta.env.VITE_API_BASE_URL || window.location.origin`.
  - `S00` already lists S16.
  - The repository is public, so scheduled Actions minutes are free.
  - S14 and S15 are on `main`, so phase 3 is not blocked and R8 includes the CMS check.
- **To change:**
  - `.github/workflows/ci.yml` runs only on `pull_request`. Render's `checksPass` needs the checks
    of the merged commit on `main`.
  - There is no `render.yaml` and no keep-alive workflow.
  - `README.md` has no *Deployment* section. `AGENTS.md` has no note about production files.
- **Render facts this plan relies on** (blueprint spec and monorepo docs):
  - `autoDeployTrigger: checksPass` deploys only when the commit's CI checks pass.
  - `buildFilter` paths are always relative to the repository root, even with `rootDir`.
  - With `rootDir`, the publish directory is relative to it, and files outside it are not
    available at build time. `vite.config.ts` calls `loadEnv(mode, "..", "")` for the local
    proxy only. Missing files are ignored, so the build does not need them.
  - Static sites take neither `region` nor `plan`.
  - The Node version comes from `NODE_VERSION`, `.node-version`, `.nvmrc` or the `engines` of
    `package.json`. Render documents only the repository root for `.nvmrc`. `web/.nvmrc` (`24`)
    and `engines` (`>=24 <25`) both resolve to the latest Node 24, so `NODE_VERSION` is not set.
    R8 checks the build log, and a follow-up adds `NODE_VERSION` only if it shows another
    version.
- **Branches:** phases 2 and 3 need phase 1 merged and R4 done, so each phase has its own branch,
  started from an up-to-date `main` after the previous phase's merge. `branch` in the frontmatter
  is the current phase's branch.
- **Testing:** these phases change configuration and documentation, not behavior, so they have no
  red-green-refactor cycle (`ai-project-tdd` allows this for behavior that cannot reasonably be
  test-first). No test parses `render.yaml` or the workflows. What Render and GitHub do with them is
  checked by the runbook.

## Manual runbook

Done by the owner, never by an agent. A phase whose required steps are unchecked stops and asks the
owner instead of starting.

- [x] **R1 · Atlas cluster** [before phase 1]: a free cluster on AWS `eu-central-1`, a database user
  for the API with read and write access to `daily-trends`, network access from `0.0.0.0/0`, and
  a URL that names the database.
- [x] **R2 · Scraping from Render** [before phase 1]: `daily-trends-api-spike` ran the migrations and
  saved feeds, with a 200 for each of the five sources.
- [x] **R3 · Remove the spike** [before phase 1]: `daily-trends-api-spike` deleted.
- [ ] **R4 · Create the Blueprint** [after phase 1 is merged]: a new Blueprint from `main`, with the
  `MONGO_URL` from R1. The first deploy passes its health check. Note the API URL.
- [ ] **R5 · First administrator** [after R4]: `create-admin` from a developer machine against Atlas,
  with a long password.
- [ ] **R6 · Check the API** [after R5]: `/status` 200, `/docs` loads, `/feed/home` answers feeds,
  `/auth/login` answers a token.
- [ ] **R7 · Keep-alive variable** [after phase 2 is merged]: the repository variable `API_URL`. A
  manual run is green. A day later, every scheduled run is green and the API logs show no restart.
- [ ] **R8 · Check the web app** [after phase 3 is merged]:
  - The Blueprint sync creates `daily-trends-web`, and its first build passes using Node 24.
  - The front page shows feeds, and a reload on a deep route opens the app.
  - The administrator logs in to the CMS and creates a feed.

## Phase 1: API on Render

Branch `chore/s16-api-on-render`. Requires R1, R2 and R3 (done). Followed by R4, R5 and R6.

`render.yaml` declares the API service only, CI also runs on `push` to `main`, and the docs explain
the platform and the first runbook steps.

### Public contracts

- `render.yaml` at the repository root, with no secret value:

  ```yaml
  services:
    - type: web
      name: daily-trends-api
      runtime: docker
      dockerfilePath: ./Dockerfile
      dockerContext: .
      plan: free
      region: frankfurt
      healthCheckPath: /status
      autoDeployTrigger: checksPass
      buildFilter:
        paths:
          - src/**
          - pyproject.toml
          - uv.lock
          - .python-version
          - Dockerfile
          - .dockerignore
      envVars:
        - key: ENV
          value: production
        - key: MONGO_URL
          sync: false
        - key: AUTH_SECRET_KEY
          generateValue: true
        - key: FORWARDED_ALLOW_IPS
          value: "*"
  ```

  `PORT` is set by Render. The scheduler keeps its defaults (on, every 2 hours).
- `.github/workflows/ci.yml`: `on: pull_request` plus `push: branches: [main]`. The jobs are the same.
- `README.md` gains a *Deployment* section:
  - the platform table and the two accounts with no card;
  - the accepted limits of the free plans;
  - how a merge deploys: CI on `main`, `checksPass` and the build filter;
  - the API and the web app deploy separately, so an API contract change is additive first;
  - runbook R1–R6, with the `create-admin` command of R5;
  - the edge cases the owner can meet: missing `MONGO_URL`, a URL without `/daily-trends`, a
    rollback that does not undo a migration.
- `AGENTS.md` notes the following:
  - `render.yaml` and `.github/workflows/keep-alive.yml` describe production;
  - agents never run runbook steps;
  - an API contract change is additive first, because the two services deploy separately.

### Tests first

- [x] No test: configuration and documentation only (see *Context · Testing*).

### Implementation

- [x] Confirm R1–R3 are checked; otherwise stop and ask the owner.
- [x] Add `render.yaml` with the API service.
- [x] Add `push` to `main` in `ci.yml`.
- [x] Add the *Deployment* section to `README.md` with the platform, the limits and R1–R6.
- [x] Add the production note to `AGENTS.md`.
- [x] Check that `render.yaml` holds no secret and that the README's runbook matches the spec.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

### Verification

- `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run lint-imports && uv run pytest`
- After the merge: R4, R5 and R6.

## Phase 2: Keep-alive

Branch `chore/s16-keep-alive`, from `main` after phase 1 is merged. Requires R4. Followed by R7.

A scheduled workflow requests `/status` every 10 minutes, so Render never stops the API. It is
skipped while `API_URL` is not set.

### Public contracts

- `.github/workflows/keep-alive.yml`:
  - `on: schedule: - cron: "*/10 * * * *"` and `workflow_dispatch`.
  - `permissions: {}`: it reads nothing from the repository.
  - One job on `ubuntu-22.04` with `if: vars.API_URL != ''` (skipped, not failed, without it) and
    a short `timeout-minutes`.
  - One step:
    `curl --fail --silent --show-error --max-time 120 --retry 3 --retry-delay 15 --retry-all-errors "$API_URL/status"`,
    with `API_URL: ${{ vars.API_URL }}` in its `env`. The time limit covers a cold start of about
    a minute plus the startup.
- `README.md` *Deployment*:
  - R7, with `API_URL` set to the URL from R4, without a trailing slash;
  - the keep-alive in the platform table;
  - the edge cases: skipped runs before R7, missed runs under load, and GitHub disabling it after
    60 days without commits;
  - a failed run emails the owner, which is the only alerting.

### Tests first

- [ ] No test: configuration and documentation only (see *Context · Testing*).

### Implementation

- [ ] Confirm phase 1 is merged and R4 is checked; otherwise stop and ask the owner.
- [ ] Create `chore/s16-keep-alive` from an up-to-date `main` and record it in `branch`.
- [ ] Add `keep-alive.yml`.
- [ ] Add R7 and the keep-alive edge cases to `README.md`.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

### Verification

- The quality gate from `AGENTS.md`.
- After the merge: before R7, the scheduled runs show as skipped. Then R7.

## Phase 3: Web app

Branch `chore/s16-web-app`, from `main` after phase 1 is merged. It does not depend on phase 2.
Requires S14 (merged) and R4, whose API URL the owner gives at the start. Followed by R8.

`render.yaml` adds the static site, built from `web/` with the API URL, with SPA rewrites and cache
headers.

### Public contracts

- `render.yaml` adds a second service:

  ```yaml
    - type: web
      name: daily-trends-web
      runtime: static
      rootDir: web
      buildCommand: corepack enable && pnpm install --frozen-lockfile && pnpm build
      staticPublishPath: dist
      autoDeployTrigger: checksPass
      buildFilter:
        paths:
          - web/**
      envVars:
        - key: VITE_API_BASE_URL
          value: https://<api>.onrender.com
        - key: COREPACK_ENABLE_DOWNLOAD_PROMPT
          value: "0"
      headers:
        - path: /assets/*
          name: Cache-Control
          value: public, max-age=31536000, immutable
        - path: /index.html
          name: Cache-Control
          value: no-cache
      routes:
        - type: rewrite
          source: /*
          destination: /index.html
  ```

  - `VITE_API_BASE_URL` is the literal URL from R4, with no trailing slash. It is not a secret,
    and changing it needs a new build.
  - `COREPACK_ENABLE_DOWNLOAD_PROMPT` is `"0"`, as in CI, so corepack never waits for a
    confirmation.
  - No `NODE_VERSION`: `web/.nvmrc` and `engines` resolve to Node 24 (see *Context*).
  - Render applies a rewrite only when no file matches the path, so `/assets/*` and other files are
    served as they are.
- `README.md` *Deployment*:
  - the web app in the platform table;
  - R8, including the check of the Node version in the build log;
  - how `VITE_API_BASE_URL` is set and that a change needs a new build;
  - the edge cases: a reload on a deep route, and a merge that changes `web/` and `src/` deploying
    both.

### Tests first

- [ ] No test: configuration and documentation only (see *Context · Testing*).

### Implementation

- [ ] Confirm phase 1 is merged and R4 is checked, and ask the owner for the API URL; otherwise stop.
- [ ] Create `chore/s16-web-app` from an up-to-date `main` and record it in `branch`.
- [ ] Add the web service to `render.yaml`.
- [ ] Add R8 and the web app's part of *Deployment* to `README.md`.
- [ ] Build locally the way Render will:
  `cd web && VITE_API_BASE_URL=https://<api>.onrender.com pnpm build`. Check that `dist/` has
  `index.html` and hashed files under `assets/`, and that the URL is in the bundle.
- [ ] Run the quality gate from `AGENTS.md` and the web quality gate, and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.

### Verification

- The quality gate from `AGENTS.md`.
- From `web/`: `pnpm biome ci . && pnpm tsc --noEmit && pnpm vitest run && pnpm build && pnpm playwright test`.
- After the merge: R8.

## Next step

Phase 1 is implemented on `chore/s16-api-on-render` and waits for review, commit and merge.
After the merge the owner runs R4, R5 and R6. Phase 2 (`chore/s16-keep-alive`) and phase 3
(`chore/s16-web-app`, with the API URL from R4) start from `main` after that.
