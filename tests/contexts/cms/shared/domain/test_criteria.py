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
    assert criteria.orders == ()
    assert criteria.limit is None


def test_criteria_keeps_its_filters_order_and_limit() -> None:
    filters = (Filter("name", "Ivan"), Filter("age", 30))

    criteria = DummyCriteria(filters=filters, orders=(Order("age", "desc"),), limit=5)

    assert criteria.filters == filters
    assert criteria.orders == (Order("age", "desc"),)
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
        DummyCriteria(orders=(Order("email", "asc"),))

    assert str(error.value) == "<DummyCriteria> does not allow the field <email>"


def test_criteria_with_the_same_values_are_equal() -> None:
    assert DummyCriteria(filters=(Filter("name", "Ivan"),), limit=1) == DummyCriteria(
        filters=(Filter("name", "Ivan"),), limit=1
    )


def test_criteria_groups_the_values_of_each_filtered_field_in_filter_order() -> None:
    criteria = DummyCriteria(
        filters=(Filter("name", "Ivan"), Filter("age", 30), Filter("name", "Ana"))
    )

    assert criteria.values_by_field() == {"name": ("Ivan", "Ana"), "age": (30,)}


def test_criteria_without_filters_has_no_values_by_field() -> None:
    assert DummyCriteria().values_by_field() == {}


def test_criteria_keeps_several_orders_and_the_position_to_start_after() -> None:
    orders = (Order("age", "desc"), Order("name", "asc"))

    criteria = DummyCriteria(orders=orders, after=(30, "Ivan"))

    assert criteria.orders == orders
    assert criteria.after == (30, "Ivan")


@pytest.mark.parametrize(
    ("orders", "after"),
    [
        ((), (30,)),
        ((Order("age", "desc"),), (30, "Ivan")),
        ((Order("age", "desc"), Order("name", "asc")), (30,)),
    ],
)
def test_criteria_rejects_a_position_without_one_value_per_order(
    orders: tuple[Order, ...], after: tuple[object, ...]
) -> None:
    with pytest.raises(ValueError) as error:
        DummyCriteria(orders=orders, after=after)

    assert str(error.value) == f"<DummyCriteria> needs one value per order to start after <{after}>"
