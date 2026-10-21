from dataclasses import dataclass, fields
from typing import ClassVar

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.shared.domain.criteria import Criteria, Order


@dataclass(frozen=True)
class FeedCriteria(Criteria):
    # Only constructor fields: the aggregate's own bookkeeping is not a feed field.
    FIELDS: ClassVar[frozenset[str]] = frozenset(field.name for field in fields(Feed) if field.init)
    # Every feed of a scraping run shares its creation date, so the id keeps their order fixed.
    LIST_ORDER: ClassVar[tuple[Order, Order]] = (Order("created_at", "desc"), Order("id", "desc"))

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.after is not None and self.orders != self.LIST_ORDER:
            raise ValueError(
                f"<{type(self).__name__}> only starts after a position in the list order"
            )
