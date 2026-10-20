from collections.abc import AsyncIterator
from datetime import timedelta

import httpx

# dishka types `provide` with an unparametrized `classmethod`; the providers below are typed.
from dishka import (
    Provider,
    Scope,
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
from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import FeedSearcher
from daily_trends_py.contexts.cms.feeds.application.update.feed_updater import FeedUpdater
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.mongo_feed_repository import (  # noqa: E501
    MongoFeedRepository,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.el_confidencial_feed_scraper import (
    ElConfidencialFeedScraper,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.el_espanol_feed_scraper import (
    ElEspanolFeedScraper,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.el_mundo_feed_scraper import (
    ElMundoFeedScraper,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.la_razon_feed_scraper import (
    LaRazonFeedScraper,
)
from daily_trends_py.contexts.cms.feeds.infrastructure.scrape.la_vanguardia_feed_scraper import (
    LaVanguardiaFeedScraper,
)
from daily_trends_py.contexts.cms.shared.domain.clock import Clock

FEED_USE_CASES = (
    FeedCreator,
    FeedFinder,
    FeedSearcher,
    FeedUpdater,
    FeedDeleter,
    FeedScraper,
    FeedHomeSearcher,
)


class FeedsProvider(Provider):
    """The feeds subdomain: its repository, scrapers, background refresher and use cases."""

    scope = Scope.APP

    feed_repository = provide(MongoFeedRepository, provides=FeedRepository)

    feed_creator = provide(FeedCreator)
    feed_finder = provide(FeedFinder)
    feed_searcher = provide(FeedSearcher)
    feed_updater = provide(FeedUpdater)
    feed_deleter = provide(FeedDeleter)
    feed_home_searcher = provide(FeedHomeSearcher)

    @provide
    def feed_scraper(
        self,
        settings: Settings,
        repository: FeedRepository,
        http_client: httpx.AsyncClient,
        clock: Clock,
    ) -> FeedScraper:
        return FeedScraper(
            repository,
            [
                ElMundoFeedScraper(http_client, clock),
                ElEspanolFeedScraper(http_client, clock),
                ElConfidencialFeedScraper(http_client, clock),
                LaRazonFeedScraper(http_client, clock),
                LaVanguardiaFeedScraper(http_client, clock),
            ],
            settings.timezone,
        )

    @provide
    async def feed_home_refresher(
        self, settings: Settings, scraper: FeedScraper, clock: Clock
    ) -> AsyncIterator[FeedHomeRefresher]:
        # A background run keeps using both clients, so it is closed before them.
        refresher = FeedHomeRefresher(
            scraper, clock, timedelta(seconds=settings.scrape_cooldown_seconds)
        )
        yield refresher
        await refresher.aclose()
