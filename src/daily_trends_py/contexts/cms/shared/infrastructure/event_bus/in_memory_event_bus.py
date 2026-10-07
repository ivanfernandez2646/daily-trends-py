from collections import defaultdict
from collections.abc import Sequence

from daily_trends_py.contexts.cms.shared.domain.event_bus import (
    DomainEvent,
    DomainEventSubscriber,
)


class InMemoryEventBus:
    def __init__(self) -> None:
        self._subscribers: defaultdict[str, list[DomainEventSubscriber]] = defaultdict(list)

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            for subscriber in self._subscribers[event.event_name]:
                await subscriber.on(event)

    def add_subscribers(self, subscribers: Sequence[DomainEventSubscriber]) -> None:
        for subscriber in subscribers:
            for event_type in subscriber.subscribed_to():
                self._subscribers[event_type.event_name].append(subscriber)
