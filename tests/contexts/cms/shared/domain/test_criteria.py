from dataclasses import dataclass
from typing import ClassVar

import pytest

from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria, Filter, Order


@dataclass(frozen=True)
class DummyCriteria(Criteria):
    FIELDS: ClassVar[frozenset[str]] = frozenset({"name", "age"})


def test_criteria_without_arguments_has_no_filters_order_or_limit() -> None:
    criteria = DummyCriteria()

    assert criteria.filters == ()
    assert criteria.order is None
    assert criteria.limit is None


def test_criteria_keeps_its_filters_order_and_limit() -> None:
    filters = (Filter("name", "Ivan"), Filter("age", 30))

    criteria = DummyCriteria(filters=filters, order=Order("age", "desc"), limit=5)

    assert criteria.filters == filters
    assert criteria.order == Order("age", "desc")
    assert criteria.limit == 5


@pytest.mark.parametrize("limit", [0, -1, True])
def test_criteria_rejects_a_limit_that_is_not_a_positive_integer(limit: int) -> None:
    with pytest.raises(ValueError) as error:
        DummyCriteria(limit=limit)

    assert str(error.value) == f"<DummyCriteria> does not allow the limit <{limit}>"


def test_criteria_rejects_a_filter_on_a_field_it_does_not_have() -> None:
    with pytest.raises(ValueError) as error:
        DummyCriteria(filters=(Filter("name", "Ivan"), Filter("email", "ivan@example.com")))

    assert str(error.value) == "<DummyCriteria> does not allow the field <email>"


def test_criteria_rejects_an_order_on_a_field_it_does_not_have() -> None:
    with pytest.raises(ValueError) as error:
        DummyCriteria(order=Order("email", "asc"))

    assert str(error.value) == "<DummyCriteria> does not allow the field <email>"


def test_criteria_with_the_same_values_are_equal() -> None:
    assert DummyCriteria(filters=(Filter("name", "Ivan"),), limit=1) == DummyCriteria(
        filters=(Filter("name", "Ivan"),), limit=1
    )
