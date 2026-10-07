---
name: ai-project-conventional-commit
description: Create one Conventional Commit when the user explicitly asks to commit changes or selects a suggested commit message.
disable-model-invocation: false
user-invocable: true
metadata:
  source: 'Based on Codely /codely-git-conventional_commit (https://codely.com)'
---

# Create a Conventional Commit

Based on Codely's `/codely-git-conventional_commit` skill and adapted for this template.

Only run after an explicit user request to commit.

1. Inspect `git status`, staged and unstaged diffs, current branch, and recent commit style.
2. Refuse to commit secrets or credentials.
3. Stage only relevant files.
4. Commit once using `resources/commit-messages.md`.
5. Add:
   `Co-Authored-By: <tool> - <model> (<reasoning-effort>) <tool-email>`.
6. Verify with `git status`.

Never amend, bypass hooks, push, or force-push unless explicitly requested and safe.
