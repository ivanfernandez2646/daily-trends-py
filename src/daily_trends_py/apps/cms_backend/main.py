import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import TracebackType

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse
from uvicorn.config import STARTUP_FAILURE

from daily_trends_py.apps.cms_backend.request_body import (
    MalformedRequestBody,
    handle_malformed_request_body,
)
from daily_trends_py.apps.cms_backend.routes import register_routes
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.feeds.application.create.feed_creator import FeedCreator
from daily_trends_py.contexts.cms.feeds.application.delete.feed_deleter import FeedDeleter
from daily_trends_py.contexts.cms.feeds.application.find.feed_finder import FeedFinder
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
from daily_trends_py.contexts.cms.shared.infrastructure.event_bus.in_memory_event_bus import (
    InMemoryEventBus,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    create_mongo_client,
)

logger = logging.getLogger(__name__)


async def _handle_unhandled_error(_request: Request, error: Exception) -> Response:
    logger.error("Unhandled error", exc_info=error)
    return PlainTextResponse(str(error), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def create_app(
    settings: Settings, http_transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        mongo_client = await create_mongo_client(settings.mongo_url)
        app.state.mongo_client = mongo_client
        event_bus = InMemoryEventBus()
        app.state.event_bus = event_bus
        feed_repository: FeedRepository = MongoFeedRepository(mongo_client)
        app.state.feed_creator = FeedCreator(feed_repository, event_bus)
        app.state.feed_finder = FeedFinder(feed_repository)
        app.state.feed_searcher = FeedSearcher(feed_repository)
        app.state.feed_home_searcher = FeedHomeSearcher(feed_repository)
        app.state.feed_updater = FeedUpdater(feed_repository)
        app.state.feed_deleter = FeedDeleter(feed_repository)
        # No timeout on purpose: a known defect kept by the port (specs/improvements, #8).
        http_client = httpx.AsyncClient(
            transport=http_transport, timeout=None, follow_redirects=True
        )
        app.state.feed_scraper = FeedScraper(
            feed_repository,
            [ElMundoFeedScraper(http_client), ElEspanolFeedScraper(http_client)],
        )
        try:
            yield
        finally:
            await http_client.aclose()
            await mongo_client.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.add_exception_handler(MalformedRequestBody, handle_malformed_request_body)
    app.add_exception_handler(Exception, _handle_unhandled_error)
    register_routes(app)
    return app


def _log_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    traceback: TracebackType | None,
) -> None:
    # The interpreter exits with code 1 after the hook returns.
    logger.critical("uncaughtException", exc_info=(exc_type, exc_value, traceback))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    sys.excepthook = _log_uncaught_exception
    try:
        settings = Settings()
        uvicorn.run(create_app(settings), host="0.0.0.0", port=settings.port)
    except SystemExit as error:
        # uvicorn logs why it could not start and exits with its own code (3).
        if error.code == STARTUP_FAILURE:
            sys.exit(1)
        raise
    except Exception:
        logger.exception("Startup failed")
        sys.exit(1)
