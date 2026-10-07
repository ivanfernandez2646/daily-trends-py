---
name: ai-project-create-plan
description: Create an implementation plan from a repository spec. Explore with subagents, agree contracts and phase granularity, then save the approved plan.
disable-model-invocation: true
user-invocable: true
metadata:
  source: 'Based on Codely /codely-plan-create-subagents (https://codely.com)'
---

# Create a Spec-First plan

Based on Codely's `/codely-plan-create-subagents` skill and adapted for this template.

Invoke as `/ai-project-create-plan specs/<feature>.md`.

## Preconditions

- Require a spec path under `specs/`. If absent, ask the user to create or choose one.
- Read `AGENTS.md` and the spec before planning.
- Do not edit production code while planning.

## Workflow

1. Explore relevant code through parallel, narrowly scoped subagents. Ask for concrete paths,
   existing contracts, tests, and conventions. Read files directly only to confirm gaps.
2. Compare findings against the spec. Surface contradictions instead of guessing.
3. Offer phase granularity: minimum, intermediate, or granular. Recommend one.
4. Propose public contracts that change: application methods, HTTP payloads, domain events,
   schemas, test suites, and user-facing copy. Omit unchanged contract types.
5. Agree contracts and phases with the user before writing the plan.
6. Save the approved plan at:
   `.agents/plans/YYYY_MM_DD-<name>/YYYY_MM_DD-<name>-plan.md`.
7. Follow the `ai-project-start-work-branch` skill after approval. Record the branch in plan frontmatter.

## Plan requirements

Each phase is a vertical slice and contains:

1. Description.
2. Public contracts.
3. Test cases to write first.
4. Implementation tasks.
5. Verification using repository commands.
6. A mandatory stop for user review.

Use the frontmatter and structure in `resources/plan-guidelines.md`.
