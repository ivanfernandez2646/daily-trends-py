---
name: ai-project-implement-phase
description: Implement exactly one unchecked phase from an approved Spec-First plan using a feature branch and TDD, then stop for review.
disable-model-invocation: true
user-invocable: true
metadata:
  source: 'Based on Codely /codely-plan_phase-implement (https://codely.com)'
---

# Implement one plan phase

Based on Codely's `/codely-plan_phase-implement` skill and adapted for this template.

Invoke as `/ai-project-implement-phase .agents/plans/<plan>/<plan>-plan.md`.

## Workflow

1. Require an approved plan path. The current phase is the first phase with an unchecked item.
2. Read `AGENTS.md`, the referenced spec, and the phase.
3. Inspect the current branch. If it is `main` or `master`, follow `ai-project-start-work-branch` before edits.
4. Follow `ai-project-tdd`. Use `ai-project-unit-testing` for stubs, Object Mothers, and test layout.
5. Implement every item in the current phase only. Never start the next phase.
6. Run the phase's verification command and the quality gate from `AGENTS.md`. Fix introduced failures.
7. Update the plan's checkboxes, next step, implementation metadata, and timestamp.
8. Stop. Summarize changes and suggest three Conventional Commit messages.

Never commit or push automatically. When the user explicitly asks to commit, the
`ai-project-conventional-commit` skill handles it.
