from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0001_feeds_indexes,
    m0002_feeds_category_and_url,
    m0004_feeds_list_indexes,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
    MongoDocument,
)

pytestmark = pytest.mark.integration

EXPECTED_INDEXES = {
    "_id_": [("_id", 1)],
    "created_at_id_desc": [("createdAt", -1), ("_id", -1)],
    "category_created_at_id_desc": [("category", 1), ("createdAt", -1), ("_id", -1)],
    "source_created_at_id_desc": [("source", 1), ("createdAt", -1), ("_id", -1)],
    "source_title_created_at": [("source", 1), ("title", 1), ("createdAt", 1)],
}

START = datetime(2026, 10, 1, tzinfo=UTC)


async def feeds_indexes(db: MongoDatabase) -> Mapping[str, Mapping[str, object]]:
    return await db["feeds"].index_information()


async def test_replaces_the_list_indexes_with_ones_that_end_in_the_id(db: MongoDatabase) -> None:
    await m0001_feeds_indexes.up(db)
    await m0002_feeds_category_and_url.up(db)

    await m0004_feeds_list_indexes.up(db)

    indexes = await feeds_indexes(db)
    assert {name: index["key"] for name, index in indexes.items()} == EXPECTED_INDEXES


async def test_creates_the_list_indexes_where_the_replaced_ones_never_existed(
    db: MongoDatabase,
) -> None:
    await m0004_feeds_list_indexes.up(db)

    indexes = await feeds_indexes(db)
    assert {name: index["key"] for name, index in indexes.items()} == {
        name: key for name, key in EXPECTED_INDEXES.items() if name != "source_title_created_at"
    }


async def test_running_it_again_changes_nothing(db: MongoDatabase) -> None:
    await m0001_feeds_indexes.up(db)
    await m0002_feeds_category_and_url.up(db)
    await m0004_feeds_list_indexes.up(db)
    first_run = await feeds_indexes(db)

    await m0004_feeds_list_indexes.up(db)

    assert await feeds_indexes(db) == first_run


def _used_indexes(plan: object) -> set[str]:
    """The names of the indexes a query plan scans, at any depth."""
    if isinstance(plan, list):
        return {name for stage in cast(list[object], plan) for name in _used_indexes(stage)}
    if not isinstance(plan, dict):
        return set()
    stage = cast(dict[str, object], plan)
    names: set[str] = {cast(str, stage["indexName"])} if "indexName" in stage else set()
    return names | {name for value in stage.values() for name in _used_indexes(value)}


def _has_blocking_sort(plan: object) -> bool:
    if isinstance(plan, list):
        return any(_has_blocking_sort(stage) for stage in cast(list[object], plan))
    if not isinstance(plan, dict):
        return False
    stage = cast(dict[str, object], plan)
    return stage.get("stage") == "SORT" or any(_has_blocking_sort(v) for v in stage.values())


@pytest.mark.parametrize(
    ("filters", "index"),
    [
        ({}, "created_at_id_desc"),
        ({"category": "SPORTS"}, "category_created_at_id_desc"),
        ({"source": "EL_MUNDO"}, "source_created_at_id_desc"),
    ],
)
async def test_a_page_of_the_list_reads_its_index_in_order(
    db: MongoDatabase, filters: MongoDocument, index: str
) -> None:
    await m0001_feeds_indexes.up(db)
    await m0002_feeds_category_and_url.up(db)
    await m0004_feeds_list_indexes.up(db)
    await db["feeds"].insert_many(
        [
            {
                "_id": f"{minute:08d}-0000-4000-8000-000000000000",
                "title": f"Feed {minute}",
                "source": ("EL_MUNDO", "CMS")[minute % 2],
                "category": ("SPORTS", "CULTURE", "POLITICS")[minute % 3],
                "createdAt": START + timedelta(minutes=minute),
            }
            for minute in range(60)
        ]
    )
    after = {
        "$or": [
            {"createdAt": {"$lt": START + timedelta(minutes=30)}},
            {"createdAt": START + timedelta(minutes=30), "_id": {"$lt": "00000030"}},
        ]
    }

    for query in (filters, {**filters, **after}):
        explanation = await (
            db["feeds"].find(query, sort=[("createdAt", -1), ("_id", -1)], limit=21).explain()
        )
        winning_plan = cast(dict[str, object], explanation["queryPlanner"])["winningPlan"]

        assert _used_indexes(winning_plan) == {index}
        assert not _has_blocking_sort(winning_plan)
