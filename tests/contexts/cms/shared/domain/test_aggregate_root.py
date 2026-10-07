from dataclasses import dataclass
from typing import ClassVar

from daily_trends_py.contexts.cms.shared.domain.aggregate_root import AggregateRoot
from daily_trends_py.contexts.cms.shared.domain.event_bus import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ThingCreated(DomainEvent):
    event_name: ClassVar[str] = "thing.created"


@dataclass(eq=False)
class Thing(AggregateRoot):
    name: str


def test_pull_domain_events_returns_recorded_events_in_order_and_clears_them() -> None:
    thing = Thing("a thing")
    first, second = ThingCreated(aggregate_id="1"), ThingCreated(aggregate_id="2")
    thing.record(first)
    thing.record(second)

    assert thing.pull_domain_events() == [first, second]
    assert thing.pull_domain_events() == []
