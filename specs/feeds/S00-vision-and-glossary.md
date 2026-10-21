# S00 · Vision and glossary

**Status:** draft · **General rule:** the port is **faithful to the current behavior** of daily-trends (Node). Anything we would like to change lives in `specs/improvements/` and is NOT implemented in this migration.

## Goal
Re-implement daily-trends in Python (FastAPI + Mongo) with the same observable behavior: same API, same status codes and bodies, same data in Mongo.

## What the system is
A news API ("feeds"). A feed is a headline with an author and an optional description. Sources: `CMS` (created by hand through the API), `EL_MUNDO`, `EL_ESPANOL`, `EL_CONFIDENCIAL`, `LA_RAZON` and `LA_VANGUARDIA` (obtained by scraping their front pages, see S06 and S08), and `EL_PAIS` (scraped by the original; no longer scraped, see S06).

## Bounded context
A single one, `cms`, with the subdomain `feeds` and, from S11, `users`.

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
| S08 | More sources | S06, S07, I02, I03 |
| S09 | Feed category and article URL | S02, S03, S04, S06, S08, I02, I07 |
| S11 | Authentication (`cms/users`, in `specs/users/`) | S01, S02, S04, S05, S06, I04, I06, I07 |
| S12 | Browse feeds: pagination, filters by source and text search | S03, S08, S09, I05, I07, I08 |
| S13 | Administrator session (`GET /auth/me`, in `specs/users/`) | S11 |
| S14 | Web app and reader (`web/`, in `specs/web/`, with the design system) | S07, S08, S09, S12 |
| S15 | Web CMS (in `specs/web/`) | S11, S12, S13, S14 |

Implementation order is the table order. S04 and S05 are independent of each other, and so are S03 and S06.

## Glossary
- **Feed:** aggregate root. Fields: `id`, `title`, `description` (nullable), `author`, `source`, `category`, `url` (nullable), `createdAt`, `updatedAt` (nullable).
- **Source:** `CMS` | `EL_PAIS` | `EL_MUNDO` | `EL_ESPANOL` | `EL_CONFIDENCIAL` | `LA_RAZON` | `LA_VANGUARDIA`.
- **Category:** `POLITICS` | `INTERNATIONAL` | `ECONOMY` | `SOCIETY` | `SPORTS` | `CULTURE` | `TECHNOLOGY` | `SCIENCE` | `HEALTH` | `OPINION` | `OTHER`. Required on every feed (see S09).
- **URL:** the original article of a scraped feed, an absolute `http(s)` URL; `null` for `CMS` feeds and feeds stored before S09.
- **Front page (home):** up to 10 feeds from the scraped sources: the 2 most recent of each, filled with the most recent of any of them (see S08).
- **Administrator:** a user who logs in to manage the CMS; every user is one (S11).
- **Scrap:** acquiring headlines from the El Mundo, El Español, El Confidencial, La Razón and La Vanguardia front pages (El País in the original; see S06 and S08).

## Out of scope
Scheduler, pagination, Django, production deployment. Known improvements are in `improvements/`.

## Source of truth for behavior
The Node reference repo (`reference/daily-trends-node`): the `.feature` files under `tests/apps/cms/backend/controllers/**` and `docs/openapi.yml`. If a spec and a `.feature` disagree, the `.feature` wins and the discrepancy is noted.
