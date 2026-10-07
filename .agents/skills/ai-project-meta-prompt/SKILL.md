---
name: ai-project-meta-prompt
description: Refine an unclear implementation request into a concise prompt with role, objective, context, constraints, and acceptance criteria.
disable-model-invocation: false
user-invocable: false
---

# Refine a prompt

When a request is too vague to become a spec, build a prompt containing:

1. Objective and user outcome.
2. Relevant repository context.
3. Constraints and explicit exclusions.
4. Public contracts that may change.
5. Verifiable acceptance criteria.

Ask only decisions that materially change the result. Look up repository facts instead of asking.
