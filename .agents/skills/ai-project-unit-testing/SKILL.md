---
name: ai-project-unit-testing
description: Write maintainable pytest unit tests with explicit fake classes, Object Mothers, and Given-When-Then structure.
disable-model-invocation: false
user-invocable: false
---

# Unit testing

Use automatically when writing unit tests.

## Test doubles

- Create a fake class that implements the real port (`typing.Protocol`), usually in memory.
- Store configured responses and call history explicitly.
- Do not use `unittest.mock`, `MagicMock`, `AsyncMock`, `monkeypatch.setattr` on imports, or
  `pytest-mock`.
- Keep fakes near tests under `tests/helpers/` or a feature-local `fakes/` folder.

## Object Mothers

- Create `<concept>_mother.py` for valid domain and DTO fixtures.
- Provide a valid default plus named variants.
- Accept keyword overrides so tests state only relevant differences.
- Use `Faker` through a shared `MotherCreator` helper for randomized primitive defaults.
- Never hide the behavior under test behind excessive fixture magic.

## Structure

Write tests in Given-When-Then order:

1. Given dependencies and input.
2. When invoking the public behavior.
3. Then assert result, state, and relevant calls.

Prefer one behavior per test and descriptive test names (`test_<behavior>_when_<condition>`).
Use `pytest.mark.parametrize` for input variations and `pytest.raises` for failures. Prefer plain
functions over test classes. Async tests are plain `async def` (`asyncio_mode = "auto"`).
Test use cases and application services; test domain objects separately only when they own
meaningful invariants.
