from collections.abc import AsyncIterator, Sequence

import httpx

# dishka types `provide` with an unparametrized `classmethod`; the providers below are typed.
from dishka import (
    Provider,
    Scope,
    from_context,
    provide,  # pyright: ignore[reportUnknownVariableType]
)

from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.shared.domain.event_bus import EventBus
from daily_trends_py.contexts.cms.shared.infrastructure.event_bus.in_memory_event_bus import (
    InMemoryEventBus,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.runner import (
    run_migrations,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    create_mongo_client,
)
from daily_trends_py.contexts.cms.shared.infrastructure.system_clock import SystemClock

HTTP_USER_AGENT = "daily-trends-py"


class InfrastructureProvider(Provider):
    """The resources every bounded context shares: settings, Mongo, HTTP, events and time.

    Resources are generators, closed in reverse order of creation, so anything built on them
    closes first.
    """

    scope = Scope.APP

    settings = from_context(provides=Settings)

    def __init__(
        self,
        http_transport: httpx.AsyncBaseTransport | None,
        migrations: Sequence[Migration],
    ) -> None:
        super().__init__()
        # `None` keeps httpx's default transport, which also honors proxy environment variables.
        self._http_transport = http_transport
        self._migrations = migrations

    @provide
    async def mongo_client(self, settings: Settings) -> AsyncIterator[MongoClient]:
        client = await create_mongo_client(settings.mongo_url)
        # Applied before anything gets the client, so the app never works on an older schema.
        try:
            await run_migrations(client.get_default_database(), self._migrations)
        except BaseException:
            await client.close()
            raise
        yield client
        await client.close()

    @provide
    async def http_client(self, settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
        client = httpx.AsyncClient(
            transport=self._http_transport,
            timeout=settings.scrap_timeout_seconds,
            headers={"User-Agent": HTTP_USER_AGENT},
            follow_redirects=True,
        )
        yield client
        await client.aclose()

    @provide
    def clock(self, settings: Settings) -> Clock:
        return SystemClock(settings.timezone)

    event_bus = provide(InMemoryEventBus, provides=EventBus)
