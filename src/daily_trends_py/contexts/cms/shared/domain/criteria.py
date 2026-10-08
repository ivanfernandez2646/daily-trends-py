from collections.abc import Mapping
from typing import Literal, TypedDict

type SortDirection = Literal["asc", "desc"]


class Criteria(TypedDict, total=False):
    """Search criteria; an absent key means no filter, no sort or no limit."""

    filter: list[Mapping[str, object]]
    """Field → value conditions combined with OR."""
    sort: Mapping[str, SortDirection]
    limit: int
    """0 means no limit."""
