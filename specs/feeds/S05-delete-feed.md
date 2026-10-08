# S05 · Delete a feed

**Status:** draft · **Fidelity:** exact. Depends on S02.

## `DELETE /feed/:id`
- Feed missing → 404; otherwise it is removed and the response is 200 with an empty body.

> **Superseded by [I01](../improvements/I01-http-contract-fixes.md):** a deleted feed answers 204 with an empty body.

- Any source can be deleted, not only CMS.
- No event is emitted (the original has a TODO for `feed.deleted`).

## Acceptance criteria
- Use-case tests: deletes existing, 404 on missing.
- Cover the `delete` `.feature` file.
