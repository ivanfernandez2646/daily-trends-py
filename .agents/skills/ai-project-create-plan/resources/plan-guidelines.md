# Plan guidelines

## Frontmatter

```yaml
---
name: '<semantic-name>'
description: '<short outcome>'
spec: 'specs/<feature>.md'
branch: '<type>/<slug>'
created_at: '<RFC3339 timestamp>'
created_by:
  tool: '<tool>'
  model: '<model>'
---
```

## Sections

- Goal
- Context
- Phases
- Next step

For every phase:

```markdown
## Phase N: Name

Description.

### Public contracts

- Contract and signature.

### Tests first

- [ ] Add a failing test for observable behavior.

### Implementation

- [ ] Add the minimum code that makes the test pass.
- [ ] Refactor without changing behavior.
- [ ] Run the quality gate from `AGENTS.md` and fix failures.
- [ ] STOP for user review. Suggest three Conventional Commit messages.
```

Plans must be independently reviewable and keep the repository green after each phase.
