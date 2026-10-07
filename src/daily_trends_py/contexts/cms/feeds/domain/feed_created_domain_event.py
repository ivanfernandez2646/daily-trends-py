from dataclasses import dataclass
from typing import ClassVar

from daily_trends_py.contexts.cms.shared.domain.event_bus import DomainEvent


@dataclass(frozen=True, kw_only=True)
class FeedCreatedDomainEvent(DomainEvent):
    event_name: ClassVar[str] = "feed.created"
    title: str
