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
    """Filters combined with OR; no filters means every item, and no limit means all of them."""

    FIELDS: ClassVar[frozenset[str]] = frozenset()
    """The domain field names that subclasses can filter and order by."""

    filters: tuple[Filter, ...] = ()
    order: Order | None = None
    limit: int | None = None

    def __post_init__(self) -> None:
        # Criteria are built by code, not from client input: an invalid one is a bug, not a 400.
        if self.limit is not None and (isinstance(self.limit, bool) or self.limit < 1):
            raise ValueError(f"<{type(self).__name__}> does not allow the limit <{self.limit}>")
        fields = [condition.field for condition in self.filters]
        if self.order is not None:
            fields.append(self.order.field)
        for field in fields:
            if field not in self.FIELDS:
                raise ValueError(f"<{type(self).__name__}> does not allow the field <{field}>")
