from collections.abc import Sequence

from daily_trends_py.contexts.cms.shared.domain.event_bus import (
    DomainEvent,
    DomainEventSubscriber,
)


class RecordingEventBus:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)

    def add_subscribers(self, subscribers: Sequence[DomainEventSubscriber]) -> None:
        pass
