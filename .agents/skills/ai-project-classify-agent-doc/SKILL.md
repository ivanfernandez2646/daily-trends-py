---
name: ai-project-classify-agent-doc
description: Classify new agent guidance as a persistent instruction, reusable skill, slash command, or automated hook before adding it.
disable-model-invocation: false
user-invocable: false
---

# Classify agent guidance

Before adding agent documentation, choose one canonical home:

- Any always-on expectation: `AGENTS.md`. Cursor, Claude, and Copilot all read it, so there is
  no `.cursor/rules/` folder. Add `.cursor/rules/*.mdc` only for guidance that needs `globs`
  path scoping or `@`-mention invocation, which `AGENTS.md` cannot express.
- Reusable multi-step capability: `.agents/skills/ai-project-<name>/SKILL.md`.
  Folder and `name` frontmatter both use the `ai-project-` prefix.
  Cursor reads that folder directly; Claude reads it through `.claude/skills`.
  Do not add `.cursor/skills`, which is a third scanned root for the same content.
- Explicit user action: set `user-invocable: true`. Cursor and Claude expose the skill as
  `/ai-project-<name>` on their own. Do not add a `commands/` file for it, which would create a
  duplicate slash entry.
- Non-optional machine enforcement: hook.

Do not duplicate bodies across providers. Use pointers or symlinks.
