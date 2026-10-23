---
name: 's17-reliable-keep-alive'
description: 'A free cron-job.org job keeps the API awake every 5 minutes, and the GitHub keep-alive workflow is deleted'
spec: 'specs/ops/S17-reliable-keep-alive.md'
branch: 'chore/s17-keep-alive'
created_at: '2026-10-23T10:22:20Z'
created_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
updated_at: '2026-10-23T10:35:00Z'
implemented_at: '2026-10-23T10:35:00Z'
implemented_by:
  tool: 'Claude Code'
  model: 'claude-opus-5-5'
---

# S17 · Reliable keep-alive

## Goal

A cron-job.org job requests `GET https://daily-trends-api.onrender.com/status` every 5 minutes, so
Render never stops the API, and emails the owner when it fails. The GitHub Actions keep-alive, which
GitHub ran only 5 times in 19 hours, is deleted. The application does not change.

## Context

- **Already true, no code change needed:**
  - `GET /status` (`apps/cms_backend/routes/status.py`) answers 200 with an empty body, without
    reading Mongo. `HEAD /status` answers 405, which is why cron-job.org (`GET`) was chosen over
    UptimeRobot (`HEAD`).
  - S00 lists S17, and S16 points to it (PR #35).
- **To change:**
  - `.github/workflows/keep-alive.yml` exists and reads the repository variable `API_URL`.
  - `docs/deployment.md` names the GitHub workflow in the platform table, in the free-plan limits,
    in the *Keep-alive* section and in runbook R7 (`API_URL` variable).
  - `AGENTS.md` (*Production*) says `render.yaml` and `keep-alive.yml` describe production.
  - No other file outside `specs/` and `.agents/plans/` mentions the workflow or `API_URL`.
- **Branch:** `chore/s17-keep-alive` starts from `docs/s17-keep-alive-and-s18-varied-categories`
  (PR #35, the S17 and S18 specs). Its pull request targets that branch until #35 is merged, then
  `main`.
- **No TDD cycle:** the phase changes documentation, a workflow and an external service, not
  application behavior. `ai-project-tdd` allows this for behavior that cannot reasonably be
  test-first; R9 is the check.

## Runbook

Done by the owner, never by an agent. The phase stops and asks if a required step is unchecked.

- [ ] **R9 · cron-job.org job** (required before phase 1 is merged): the job from the spec is
  created, its manual run answers 200, and a day later its history shows only 200s (or the failures
  of a deploy) and the API did not restart.
- [ ] **R10 · Remove the GitHub variable** (after phase 1 is merged): the *Keep-alive* workflow is
  gone from the *Actions* tab and the `API_URL` repository variable is deleted.

## Phase 1: cron-job.org keep-alive

Delete the GitHub workflow and document the cron-job.org job as production's keep-alive. Written
before R9 is done; merged only after R9's first day is green, so the API always has a keep-alive.

### Public contracts

- `.github/workflows/keep-alive.yml`: deleted. No workflow reads `vars.API_URL`.
- `docs/deployment.md`:
  - platform table row *Keep-alive*: cron-job.org job, plan free;
  - free-plan limits: the keep-alive (not "a workflow") prevents the stop;
  - *Keep-alive* section rewritten: `GET /status` every 5 minutes from cron-job.org; Render's health
    checks do not count; the 30-second timeout after a deploy (one failed run, then recovery); emails
    on failure, recovery and when the job is disabled after 25 failures in a row; it learns only the
    public URL; why GitHub Actions was dropped;
  - runbook R7 becomes *R7 · Keep-alive job*, with the job settings of the spec's R9.
- `AGENTS.md` *Production*: `render.yaml` describes production, and the keep-alive is the
  cron-job.org job in `docs/deployment.md`.

### Tests first

- [x] None: no application behavior changes (see *Context*). The existing suite must stay green.

### Implementation

- [x] Delete `.github/workflows/keep-alive.yml`.
- [x] Rewrite the keep-alive parts of `docs/deployment.md` listed above, and replace R7.
- [x] Update the production note in `AGENTS.md`, which also lists S17 among the deployment specs.
- [x] `grep -rn "keep-alive.yml\|API_URL" --exclude-dir=specs --exclude-dir=.agents --exclude-dir=node_modules .`
  finds nothing.
- [x] Run the quality gate from `AGENTS.md` and fix failures.
- [x] STOP for user review. Suggest three Conventional Commit messages.

## Next step

Phase 1 is implemented and waits for review. The owner does R9; the phase's pull request is merged
once R9's first day is green, then the owner does R10.
