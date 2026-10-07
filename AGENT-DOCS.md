# Agent documentation

`AGENTS.md` is the provider-neutral entry point. `.agents/` is the only shared agent folder:

- `.agents/skills/`: reusable skills discovered by agents.
- `.agents/plans/`: approved Spec-First implementation plans.

Cursor reads `.agents/skills/` directly. Claude reads the same folder through the
`.claude/skills` symlink, because Claude only discovers skills under `.claude/skills`.
Do not add `.cursor/skills`: it is a third scanned root for the same content.
Skill folders and their `name` frontmatter use the `ai-project-` prefix.

Skills with `user-invocable: true` are already exposed as `/<name>` by both Cursor and Claude.
There is no `commands/` folder: a command file with the same name as a skill produces a second
identical slash entry.

All always-on guidance lives in `AGENTS.md`, which Cursor, Claude, and Copilot read. There is no
`.cursor/rules/` folder: `alwaysApply` rules would load alongside `AGENTS.md`, not instead of it.

Do not add a singular `.agent/` folder or duplicate skill content in vendor directories.
