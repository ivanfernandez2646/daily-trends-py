from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from daily_trends_py.contexts.cms.shared.domain.event_bus import DomainEvent
from daily_trends_py.contexts.cms.shared.infrastructure.event_bus.in_memory_event_bus import (
    InMemoryEventBus,
)


@dataclass(frozen=True, kw_only=True)
class ThingCreated(DomainEvent):
    event_name: ClassVar[str] = "thing.created"


@dataclass(frozen=True, kw_only=True)
class ThingDeleted(DomainEvent):
    event_name: ClassVar[str] = "thing.deleted"


class RecordingSubscriber:
    def __init__(self, subscribed_to: Sequence[type[DomainEvent]]) -> None:
        self._subscribed_to = subscribed_to
        self.received: list[DomainEvent] = []

    def subscribed_to(self) -> Sequence[type[DomainEvent]]:
        return self._subscribed_to

    async def on(self, event: DomainEvent) -> None:
        self.received.append(event)


async def test_publish_delivers_each_event_to_its_subscribers_only() -> None:
    created_subscriber = RecordingSubscriber([ThingCreated])
    deleted_subscriber = RecordingSubscriber([ThingDeleted])
    event_bus = InMemoryEventBus()
    event_bus.add_subscribers([created_subscriber, deleted_subscriber])
    event = ThingCreated(aggregate_id="thing-id")

    await event_bus.publish([event])

    assert created_subscriber.received == [event]
    assert deleted_subscriber.received == []


async def test_publish_without_subscribers_completes() -> None:
    event_bus = InMemoryEventBus()

    await event_bus.publish([ThingCreated(aggregate_id="thing-id")])
