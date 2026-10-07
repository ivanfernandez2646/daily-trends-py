from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar, Protocol
from uuid import uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_name: ClassVar[str]
    aggregate_id: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_on: datetime = field(default_factory=lambda: datetime.now(UTC))


class DomainEventSubscriber(Protocol):
    def subscribed_to(self) -> Sequence[type[DomainEvent]]: ...

    async def on(self, event: DomainEvent) -> None: ...


class EventBus(Protocol):
    async def publish(self, events: Sequence[DomainEvent]) -> None: ...

    def add_subscribers(self, subscribers: Sequence[DomainEventSubscriber]) -> None: ...
