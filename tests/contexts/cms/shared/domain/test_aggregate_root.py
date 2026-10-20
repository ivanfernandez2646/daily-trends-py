from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from daily_trends_py.contexts.cms.shared.domain.aggregate_root import AggregateRoot
from daily_trends_py.contexts.cms.shared.domain.event_bus import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ThingCreated(DomainEvent):
    event_name: ClassVar[str] = "thing.created"


@dataclass(eq=False)
class Thing(AggregateRoot):
    name: str

    def renamed(self, name: str) -> Thing:
        thing = Thing(name)
        thing._keep_events_of(self)
        return thing


NOW = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)


def _created(id: str) -> ThingCreated:
    return ThingCreated(aggregate_id=id, occurred_on=NOW)


def test_pull_domain_events_returns_recorded_events_in_order_and_clears_them() -> None:
    thing = Thing("a thing")
    first, second = _created("1"), _created("2")
    thing.record(first)
    thing.record(second)

    assert thing.pull_domain_events() == [first, second]
    assert thing.pull_domain_events() == []


def test_a_derived_aggregate_keeps_the_pending_events_in_order_before_its_own() -> None:
    thing = Thing("a thing")
    first, second, third = _created("1"), _created("2"), _created("3")
    thing.record(first)
    thing.record(second)

    renamed = thing.renamed("another thing")
    renamed.record(third)

    assert renamed.pull_domain_events() == [first, second, third]
