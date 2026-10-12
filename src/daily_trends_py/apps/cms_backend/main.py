import logging
import sys
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from importlib.metadata import version
from types import TracebackType

import uvicorn
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from uvicorn.config import STARTUP_FAILURE

from daily_trends_py.apps.cms_backend.api import CmsBackendApi
from daily_trends_py.apps.cms_backend.container import FEED_USE_CASES, create_container
from daily_trends_py.apps.cms_backend.errors import register_exception_handlers
from daily_trends_py.apps.cms_backend.routes import register_routes
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    MIGRATIONS,
)

logger = logging.getLogger(__name__)

DESCRIPTION = (
    "Front-page news feeds: CMS feeds managed through this API and headlines scraped from"
    ' El Mundo and El Español. Every error answers `{"error": "<message>"}`: 400 for an invalid'
    " request, 404 for a missing feed, 409 for an existing id and 500 for anything else."
)


def create_app(container: AsyncContainer) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        try:
            # Built at startup, not on the first request, so an unreachable Mongo or a failing
            # migration stops startup before the app takes traffic.
            for use_case in FEED_USE_CASES:
                await container.get(use_case)
            yield
        finally:
            await container.close()

    app = CmsBackendApi(
        title="Daily trends",
        version=version("daily-trends-py"),
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    register_routes(app)
    setup_dishka(container, app)
    return app


def _log_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    traceback: TracebackType | None,
) -> None:
    # The interpreter exits with code 1 after the hook returns.
    logger.critical("uncaughtException", exc_info=(exc_type, exc_value, traceback))


def main(migrations: Sequence[Migration] = MIGRATIONS) -> None:
    logging.basicConfig(level=logging.INFO)
    sys.excepthook = _log_uncaught_exception
    try:
        settings = Settings()
        container = create_container(settings, migrations=migrations)
        uvicorn.run(create_app(container), host="0.0.0.0", port=settings.port)
    except SystemExit as error:
        # uvicorn logs why it could not start and exits with its own code (3).
        if error.code == STARTUP_FAILURE:
            sys.exit(1)
        raise
    except Exception:
        logger.exception("Startup failed")
        sys.exit(1)
