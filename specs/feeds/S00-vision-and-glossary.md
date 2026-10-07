# S00 · Vision and glossary

**Status:** draft · **General rule:** the port is **faithful to the current behavior** of daily-trends (Node). Anything we would like to change lives in `specs/improvements/` and is NOT implemented in this migration.

## Goal
Re-implement daily-trends in Python (FastAPI + Mongo) with the same observable behavior: same API, same status codes and bodies, same data in Mongo.

## What the system is
A news API ("feeds"). A feed is a headline with an author and an optional description. Sources: `CMS` (created by hand through the API), `EL_PAIS` and `EL_MUNDO` (obtained by scraping their front pages).

## Bounded context
A single one, `cms/feeds`.

## How the specs are organized
Each spec is a **capability** and is self-contained: it holds its own HTTP contract, domain rules, persistence needs, edge cases and acceptance criteria, so tasks and vertical slices can be derived from it directly. A rule is defined in the first spec that needs it and referenced by the later ones.

| Spec | Capability | Depends on |
|---|---|---|
| S01 | Foundation: app startup, config, Mongo connection, error format, `GET /status` | — |
| S02 | Create and find a feed | S01 |
| S03 | List feeds | S02 |
| S04 | Update a feed | S02 |
| S05 | Delete a feed | S02 |
| S06 | Scrape external sources | S02 |
| S07 | Front page | S03, S06 |

Implementation order is the table order. S04 and S05 are independent of each other, and so are S03 and S06.

## Glossary
- **Feed:** aggregate root. Fields: `id`, `title`, `description` (nullable), `author`, `source`, `createdAt`, `updatedAt` (nullable).
- **Source:** `CMS` | `EL_PAIS` | `EL_MUNDO`.
- **Front page (home):** the 10 most recent feeds from external sources.
- **Scrap:** acquiring headlines from the El País and El Mundo front pages.

## Out of scope
Authentication, scheduler, pagination, Django, production deployment. Known improvements are in `improvements/`.

## Source of truth for behavior
The Node reference repo (`reference/daily-trends-node`): the `.feature` files under `tests/apps/cms/backend/controllers/**` and `docs/openapi.yml`. If a spec and a `.feature` disagree, the `.feature` wins and the discrepancy is noted.
