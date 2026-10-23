# S17 · Reliable keep-alive

**Status:** draft · **Fidelity:** no application change (the API and the web app behave as in S14
and S15). Depends on S16. Replaces the keep-alive of S16.

## Goal
Keep the production API awake all day. S16's keep-alive, a GitHub Actions scheduled workflow every
10 minutes, ran only 5 times in its first 19 hours (gaps of 2 to 5 hours): GitHub delays and drops
scheduled runs under load and does not guarantee them. Each run found the API already stopped, so
in practice it slept most of the day and the first visitor paid a cold start of about a minute.

The fix keeps S16's rules: free plans only, no payment method on any account, nothing that can
charge, and no secret or repository access handed to a third party.

## Decision: cron-job.org
An external HTTP cron service requests `GET <API_URL>/status` every 5 minutes, well inside Render's
15 minutes. cron-job.org is chosen because:
- It is entirely free, with no paid plans, so there is no card to give and nothing to upsell. It is
  funded by donations and has run for more than 15 years; its code is open source (GPL).
- It sends a `GET`, which `/status` already answers with 200 (S01), so the API does not change.
- It runs jobs up to every minute, so 5 minutes leaves a wide margin and stays within fair use.
- It only learns a URL that is already public. It gets no token, no GitHub authorization, no access
  to Render or Atlas, and no data from the API: `/status` answers an empty body.
- It emails the owner when a run fails and when the API answers again: the alerting S16 lacked.

Considered and set aside:
- **UptimeRobot** Free plan: well known, but it checks with `HEAD`, which `/status` answers with 405,
  and choosing the method is not guaranteed on the Free plan. Using it would need an API change,
  and the Free plan belongs to a company that sells paid ones.
- **Better Stack** Free plan: fewer monitors and a product built to upsell; no advantage here.
- **A paid Render instance**: against S16's no-cost rule.

## The GitHub workflow is removed
`keep-alive.yml` is deleted. A backup that runs a few times a day does not keep the API awake, and
two callers mean two places to look when something fails. Removing it also removes the 60-day rule
of S16 (GitHub disables scheduled workflows without commits) and the `API_URL` repository variable,
which nothing else reads.

The workflow is deleted only after the cron-job.org job is green (R9), so the API is never left
without a keep-alive.

## Repository changes
- `.github/workflows/keep-alive.yml` is deleted.
- `docs/deployment.md`:
  - the platform table: *Keep-alive* is a cron-job.org job, plan free;
  - the free-plan limits say the keep-alive prevents the stop;
  - the *Keep-alive* section describes the cron-job.org job: what it requests and how often, the
    30-second timeout after a deploy, the email alerts, the job disabled after 25 failures, and why
    GitHub Actions was dropped;
  - the runbook, which rebuilds production from scratch, replaces R7 (the `API_URL` variable) with
    the cron-job.org job of R9 below, as *R7 · Keep-alive job*.
- `AGENTS.md`: the production note names `render.yaml` and the cron-job.org job described in
  `docs/deployment.md`, instead of `keep-alive.yml`.

## Manual runbook
Done by the owner, never by an agent.

9. **R9 · cron-job.org job** [before phase 1 is merged]
   - Create a free cron-job.org account with an email and a password from a password manager, and
     turn on two-factor authentication if the account settings offer it. Do not sign in with
     GitHub: the job needs no access to it. Nothing asks for a card; if something does, stop.
   - Create one job:
     - title `daily-trends-api keep-alive`;
     - URL `https://daily-trends-api.onrender.com/status`;
     - schedule every 5 minutes;
     - request method `GET`, no headers, no body, no authentication;
     - notifications by email on failure, on recovery, and when the job is disabled.
   - Run it once by hand from the dashboard: it answers 200.
   - A day later, the job's history shows every run with 200, or only the failures of a deploy, and
     the API logs show no startup between scheduled scrapes, so it never restarted.
10. **R10 · Remove the GitHub variable** [after phase 1 is merged]
    - The *Keep-alive* workflow no longer appears in the *Actions* tab.
    - Delete the repository variable `API_URL` in *Settings → Secrets and variables → Actions →
      Variables*.

## Phases
| Phase | Repository changes | Requires | Followed by |
|---|---|---|---|
| 1 · cron-job.org keep-alive | delete `keep-alive.yml`; `docs/deployment.md`; `AGENTS.md` | R9 | R10 |

R9 needs nothing from the repository, so it is done first; the phase can be written before it, but
is not merged until R9's first day is green.

## Testing approach
- This spec changes documentation, a workflow and an external service, not application behavior, so
  it has no red-green-refactor cycle; the plan records this, as `ai-project-tdd` asks.
- The job itself is checked by R9, not by a test.
- Verification: the quality gate from `AGENTS.md` (unchanged by a docs change).

## Out of scope
A status page, alert channels other than email, monitoring other routes or the web app (a static
site does not sleep), checks that read Mongo, `HEAD /status`, and any paid plan.

## Edge cases
- cron-job.org closes a request after 30 seconds. A deploy restarts the API and a cold start can
  take longer → that run fails and an email says so, but the request has already woken the API, and
  the next run answers 200 and emails the recovery. Accepted.
- cron-job.org disables a job after more than 25 failures in a row (about 2 hours at 5 minutes) and
  emails the owner → the API was down that long anyway; once it is fixed, the owner enables the job
  again.
- cron-job.org is down → the API stops after 15 minutes and the next visitor starts it in about a
  minute, as before S16's keep-alive. Accepted.
- cron-job.org stops existing or starts charging → the replacement is another free HTTP cron or
  monitor that sends `GET`, through a new spec and runbook step.
- The API really fails (a bad deploy that passed its health check, Atlas down) → `/status` still
  answers 200 because it does not read Mongo, so the job does not see it. Same as S16.
- Render's free hours: one service always on uses about 744 of the 750 hours a month, as S16
  already assumed.

## Acceptance criteria
- `.github/workflows/keep-alive.yml` no longer exists, and no file outside `specs/` and `.agents/plans/`
  mentions it.
- `docs/deployment.md` describes cron-job.org as the keep-alive and its runbook R7 creates the job;
  `AGENTS.md` names the job instead of the workflow. S16 points to this spec and S00 lists S17
  (done with this spec).
- No file under `src/`, `tests/` or `web/` changes.
- The quality gate passes.
- R9 and R10 pass.
