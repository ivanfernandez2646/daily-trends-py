import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)


@pytest.mark.parametrize(
    "field", ["id", "title", "description", "author", "source", "created_at", "updated_at"]
)
def test_feed_criteria_accepts_every_feed_field(field: str) -> None:
    criteria = FeedCriteria(filters=(Filter(field, None),), order=Order(field, "asc"))

    assert criteria.order == Order(field, "asc")


@pytest.mark.parametrize("field", ["createdAt", "_id", "_domain_events"])
def test_feed_criteria_rejects_a_field_that_is_not_a_feed_field(field: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        FeedCriteria(order=Order(field, "desc"))

    assert str(error.value) == f"<FeedCriteria> does not allow the field <{field}>"
