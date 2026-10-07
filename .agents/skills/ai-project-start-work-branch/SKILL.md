---
name: ai-project-start-work-branch
description: Automatically create the plan's work branch before implementation when the repository is on its default branch.
disable-model-invocation: false
user-invocable: false
---

# Start a work branch

Used automatically by `ai-project-create-plan` and `ai-project-implement-phase`.

1. Inspect the current branch and working tree.
2. Never discard or overwrite local changes.
3. If already on a non-default branch suitable for the plan, keep it.
4. Otherwise fetch the default branch when a remote exists, update it safely, then create:
   - `feat/<plan-slug>` for new behavior
   - `fix/<plan-slug>` for a bug
   - `refactor/<plan-slug>` for behavior-preserving changes
   - `chore/<plan-slug>` for maintenance
5. Record the branch in plan frontmatter.

Never implement or commit directly on `main` or `master`.
