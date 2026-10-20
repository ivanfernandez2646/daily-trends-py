from dataclasses import dataclass, field

from daily_trends_py.contexts.cms.shared.domain.event_bus import DomainEvent


@dataclass(eq=False)
class AggregateRoot:
    _domain_events: list[DomainEvent] = field(
        default_factory=list[DomainEvent], init=False, repr=False
    )

    def record(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def _keep_events_of(self, original: AggregateRoot) -> None:
        """An aggregate derived from `original` still has to publish what it recorded."""
        self._domain_events = [*original._domain_events, *self._domain_events]

    def pull_domain_events(self) -> list[DomainEvent]:
        events, self._domain_events = self._domain_events, []
        return events
