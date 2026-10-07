---
name: ai-project-tdd
description: Apply red-green-refactor automatically while implementing every plan phase.
disable-model-invocation: false
user-invocable: false
---

# Test-driven development

Used automatically by `ai-project-implement-phase`.

For each observable behavior:

1. **Red:** write the smallest test that describes the behavior. Run it and confirm it fails for
   the expected reason.
2. **Green:** add the minimum production code needed to pass. Run the focused test.
3. **Refactor:** improve names and structure without changing behavior. Run the focused suite.
4. Run the relevant broader suite before closing the phase.

Use `ai-project-unit-testing` for test-double and Object Mother patterns.

Do not write trivial tests that restate implementation details. Test public behavior, failures, and
important edge cases. If a behavior cannot reasonably be test-first, record why in the plan.
