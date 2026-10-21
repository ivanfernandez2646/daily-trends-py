from datetime import UTC, datetime

import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order


@pytest.mark.parametrize(
    "field", ["id", "title", "description", "author", "source", "created_at", "updated_at"]
)
def test_feed_criteria_accepts_every_feed_field(field: str) -> None:
    criteria = FeedCriteria(filters=(Filter(field, None),), orders=(Order(field, "asc"),))

    assert criteria.orders == (Order(field, "asc"),)


@pytest.mark.parametrize("field", ["createdAt", "_id", "_domain_events"])
def test_feed_criteria_rejects_a_field_that_is_not_a_feed_field(field: str) -> None:
    with pytest.raises(ValueError) as error:
        FeedCriteria(orders=(Order(field, "desc"),))

    assert str(error.value) == f"<FeedCriteria> does not allow the field <{field}>"


def test_feed_criteria_lists_newest_first_with_the_id_breaking_ties() -> None:
    assert (Order("created_at", "desc"), Order("id", "desc")) == FeedCriteria.LIST_ORDER


def test_feed_criteria_starts_after_a_position_in_the_list_order() -> None:
    after = (datetime(2026, 10, 21, tzinfo=UTC), "9d5b8b0e-4b0e-4c55-9f0e-2a4a1d6b3c11")

    criteria = FeedCriteria(orders=FeedCriteria.LIST_ORDER, after=after)

    assert criteria.after == after


def test_feed_criteria_rejects_a_position_in_another_order() -> None:
    with pytest.raises(ValueError) as error:
        FeedCriteria(
            orders=(Order("created_at", "asc"), Order("id", "asc")),
            after=(datetime(2026, 10, 21, tzinfo=UTC), "9d5b8b0e-4b0e-4c55-9f0e-2a4a1d6b3c11"),
        )

    assert str(error.value) == "<FeedCriteria> only starts after a position in the list order"


def test_feed_criteria_searches_text_in_the_title_and_the_description() -> None:
    criteria = FeedCriteria(orders=FeedCriteria.LIST_ORDER, text="madrid")

    assert frozenset({"title", "description"}) == FeedCriteria.TEXT_FIELDS
    assert criteria.text == "madrid"


def test_feed_criteria_rejects_a_text_in_another_order() -> None:
    with pytest.raises(ValueError) as error:
        FeedCriteria(orders=(Order("created_at", "desc"),), text="madrid")

    assert str(error.value) == "<FeedCriteria> only searches text in the list order"
