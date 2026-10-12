from collections.abc import AsyncIterator, Sequence
from datetime import timedelta

import httpx

# dishka types `provide` with an unparametrized `classmethod`; the providers below are typed.
from dishka import (
    AsyncContainer,
    Provider,
    Scope,
    from_context,
    make_async_container,
    provide,  # pyright: ignore[reportUnknownVariableType]
)

from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.feeds.application.create.feed_creator import FeedCreator
from daily_trends_py.contexts.cms.feeds.application.delete.feed_deleter import FeedDeleter
from daily_trends_py.contexts.cms.feeds.application.find.feed_finder import FeedFinder
from daily_trends_py.contexts.cms.feeds.application.home.feed_home_refresher import (
    FeedHomeRefresher,
)
from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import FeedSearcher
from daily_trends_py.contexts.cms.feeds.application.update.feed_updater import FeedUpdater
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.el_espanol_feed_scraper import (
    ElEspanolFeedScraper,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrap.el_mundo_feed_scraper import (
    ElMundoFeedScraper,
)
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
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    MIGRATIONS,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    create_mongo_client,
)
from daily_trends_py.contexts.cms.shared.infrastructure.system_clock import SystemClock

SCRAP_USER_AGENT = "daily-trends-py"

FEED_USE_CASES = (
    FeedCreator,
    FeedFinder,
    FeedSearcher,
    FeedUpdater,
    FeedDeleter,
    FeedScraper,
    FeedHomeSearcher,
)


class CmsBackendProvider(Provider):
    """The app's wiring: one instance of everything per container.

    Resources are generators, closed in reverse order of creation: the refresher, which a
    background run keeps using both clients, closes before them.
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
            headers={"User-Agent": SCRAP_USER_AGENT},
            follow_redirects=True,
        )
        yield client
        await client.aclose()

    @provide
    def clock(self, settings: Settings) -> Clock:
        return SystemClock(settings.timezone)

    event_bus = provide(InMemoryEventBus, provides=EventBus)
    feed_repository = provide(MongoFeedRepository, provides=FeedRepository)

    feed_creator = provide(FeedCreator)
    feed_finder = provide(FeedFinder)
    feed_searcher = provide(FeedSearcher)
    feed_updater = provide(FeedUpdater)
    feed_deleter = provide(FeedDeleter)
    feed_home_searcher = provide(FeedHomeSearcher)

    @provide
    def feed_scraper(
        self, settings: Settings, repository: FeedRepository, http_client: httpx.AsyncClient
    ) -> FeedScraper:
        return FeedScraper(
            repository,
            [ElMundoFeedScraper(http_client), ElEspanolFeedScraper(http_client)],
            settings.timezone,
        )

    @provide
    async def feed_home_refresher(
        self, settings: Settings, scraper: FeedScraper, clock: Clock
    ) -> AsyncIterator[FeedHomeRefresher]:
        refresher = FeedHomeRefresher(
            scraper, clock, timedelta(seconds=settings.scrap_cooldown_seconds)
        )
        yield refresher
        await refresher.aclose()


def create_container(
    settings: Settings,
    *overrides: Provider,
    http_transport: httpx.AsyncBaseTransport | None = None,
    migrations: Sequence[Migration] = MIGRATIONS,
) -> AsyncContainer:
    """`overrides` are providers declared with `override=True`, such as fakes in tests."""
    return make_async_container(
        CmsBackendProvider(http_transport, migrations), *overrides, context={Settings: settings}
    )
