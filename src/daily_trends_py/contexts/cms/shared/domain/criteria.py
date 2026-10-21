from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, Literal

type SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True)
class Filter:
    """The condition `field` equals `value`."""

    field: str
    value: object


@dataclass(frozen=True)
class Order:
    field: str
    direction: SortDirection


@dataclass(frozen=True)
class Criteria:
    """Filters on different fields combined with AND, and on the same field with OR.

    No filters means every item, and no limit means all of them.
    """

    FIELDS: ClassVar[frozenset[str]] = frozenset()
    """The domain field names that subclasses can filter and order by."""

    filters: tuple[Filter, ...] = ()
    orders: tuple[Order, ...] = ()
    limit: int | None = None
    after: tuple[object, ...] | None = None
    """The position to start strictly after: one value per order, in the same order."""

    def __post_init__(self) -> None:
        # Criteria are built by code, not from client input: an invalid one is a bug, not a 400.
        if self.limit is not None and (isinstance(self.limit, bool) or self.limit < 1):
            raise ValueError(f"<{type(self).__name__}> does not allow the limit <{self.limit}>")
        if self.after is not None and len(self.after) != len(self.orders):
            raise ValueError(
                f"<{type(self).__name__}> needs one value per order to start after <{self.after}>"
            )
        fields = [condition.field for condition in self.filters]
        fields.extend(order.field for order in self.orders)
        for field in fields:
            if field not in self.FIELDS:
                raise ValueError(f"<{type(self).__name__}> does not allow the field <{field}>")

    def values_by_field(self) -> Mapping[str, tuple[object, ...]]:
        """The accepted values of each filtered field: an item matches when every field has one."""
        values: dict[str, tuple[object, ...]] = {}
        for condition in self.filters:
            values[condition.field] = (*values.get(condition.field, ()), condition.value)
        return values
