# dishka types `provide` with an unparametrized `classmethod`; the providers below are typed.
from dishka import (
    Provider,
    Scope,
    provide,  # pyright: ignore[reportUnknownVariableType]
)

from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.shared.domain.event_bus import EventBus
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.shared.fakes.recording_event_bus import RecordingEventBus


class FakesProvider(Provider):
    """Replaces the app's persistence and event bus with in-memory fakes."""

    scope = Scope.APP

    def __init__(
        self,
        repository: InMemoryFeedRepository | None = None,
        event_bus: RecordingEventBus | None = None,
    ) -> None:
        super().__init__()
        self._repository = repository or InMemoryFeedRepository()
        self._event_bus = event_bus or RecordingEventBus()

    @provide(override=True)
    def repository(self) -> FeedRepository:
        return self._repository

    @provide(override=True)
    def event_bus(self) -> EventBus:
        return self._event_bus
